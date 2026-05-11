import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function NotFound() {
  useDocumentTitle("Sayfa bulunamadı");
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-md pt-20">
      <Card>
        <CardHeader>
          <CardTitle>404</CardTitle>
          <CardDescription>Aradığınız sayfa bulunamadı.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => navigate("/")}>Dashboard'a dön</Button>
        </CardContent>
      </Card>
    </div>
  );
}
