/**
 * Login sayfası — backend Adım 4 /api/v1/auth/login.
 *
 * - RHF + zod validation
 * - Doğru giriş → token sakla → home'a redirect
 * - Yanlış giriş → toast Türkçe (backend mesajı: "Email veya şifre yanlış")
 *
 * Register link YOK — single-user proje, kullanıcı CLI ile yaratılır
 * (backend/scripts/create_user.py).
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { apiGet, apiPost, getErrorMessage } from "@/lib/api";
import { setAuth } from "@/lib/auth";
import { useAuthStore } from "@/stores/useAuth";
import type { TokenResponse, User } from "@/types/api";

const loginSchema = z.object({
  email: z.string().email("Geçerli bir e-posta girin"),
  password: z.string().min(1, "Şifre gerekli"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

interface LocationState {
  from?: string;
}

export function Login() {
  useDocumentTitle("Giriş");

  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((s) => s.login);
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as LocationState | null)?.from ?? "/";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginFormValues) {
    setSubmitting(true);
    try {
      const tokens = await apiPost<TokenResponse>(
        "/api/v1/auth/login",
        values
      );
      // Tokens'i geçici olarak localStorage'a yaz ki /me interceptor'ı kullansın
      setAuth(tokens.access_token, tokens.refresh_token, {
        id: "",
        email: values.email,
        full_name: null,
        is_active: true,
        is_admin: false,
        created_at: new Date().toISOString(),
      });
      const user = await apiGet<User>("/api/v1/auth/me");
      login(tokens.access_token, tokens.refresh_token, user);
      toast.success("Giriş başarılı", { duration: 3000 });
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error), { duration: 5000 });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-binance-bg p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-3xl">📊</span>
            <span className="text-2xl font-medium text-binance-text-primary">
              MarketLens
            </span>
          </div>
          <CardTitle>Giriş Yap</CardTitle>
          <CardDescription>
            Kişisel kripto + emtia karar destek terminali
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">E-posta</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="orhanakkustr@gmail.com"
                {...register("email")}
                disabled={submitting}
              />
              {errors.email && (
                <p className="text-xs text-binance-short">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Şifre</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
                disabled={submitting}
              />
              {errors.password && (
                <p className="text-xs text-binance-short">
                  {errors.password.message}
                </p>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Giriş yap
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
