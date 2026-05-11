/**
 * Auth gate — token yoksa /login'e redirect + toast.
 *
 * Inline mount sırasında toast etmek strict-mode'da çift trigger olabilir,
 * o yüzden useEffect ile yönlendir + bir kez toast.
 */
import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { toast } from "sonner";

import { useAuthStore } from "@/stores/useAuth";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      toast.info("Lütfen önce giriş yapın", { duration: 3000 });
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
