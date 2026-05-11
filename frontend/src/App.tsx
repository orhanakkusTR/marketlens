import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";
import { Dashboard } from "@/pages/Dashboard";
import { Login } from "@/pages/Login";
import { NotFound } from "@/pages/NotFound";
import { SymbolDetail } from "@/pages/SymbolDetail";
import {
  Glossary,
  Heatmap,
  Journal,
  Risk,
  Scanner,
  Settings,
} from "@/pages/placeholders";

function App() {
  return (
    <BrowserRouter>
      <Toaster />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />

        {/* Protected — AppShell layout */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="/symbol/:code" element={<SymbolDetail />} />
          <Route path="/heatmap" element={<Heatmap />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/glossary" element={<Glossary />} />
        </Route>

        {/* 404 */}
        <Route path="/404" element={<NotFound />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
