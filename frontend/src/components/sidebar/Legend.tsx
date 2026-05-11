/**
 * Sidebar lejantı — KALİTE + YÖN, collapsible.
 *
 * State persistence: localStorage key `marketlens:sidebar:legend_open`.
 * Default: açık (ilk kullanıcı için). KALİTE ve YÖN aynı collapse altında.
 */
import { Minus, Plus } from "lucide-react";
import { useEffect, useState } from "react";

const STORAGE_KEY = "marketlens:sidebar:legend_open";

interface QualityItem {
  color: string;
  label: string;
  desc: string;
}

const QUALITY_ITEMS: ReadonlyArray<QualityItem> = [
  { color: "#02C076", label: "A·B", desc: "İyi setup" },
  { color: "#FCD535", label: "C", desc: "Orta setup" },
  { color: "#FF9933", label: "D", desc: "Zayıf setup" },
  { color: "#F84960", label: "DUR", desc: "Açma" },
  { color: "#1976D2", label: "Yeni", desc: "Veri yok" },
];

interface DirectionItem {
  icon: string;
  color: string;
  label: string;
  desc: string;
}

const DIRECTION_ITEMS: ReadonlyArray<DirectionItem> = [
  { icon: "▲", color: "#02C076", label: "Long", desc: "Yukarı yönlü" },
  { icon: "▼", color: "#F84960", label: "Short", desc: "Aşağı yönlü" },
  { icon: "◇", color: "#848E9C", label: "Nötr", desc: "Yön yok" },
];

function readInitial(): boolean {
  if (typeof window === "undefined") return true;
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === null ? true : v === "true";
}

export function Legend() {
  const [open, setOpen] = useState<boolean>(readInitial);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(open));
  }, [open]);

  return (
    <div className="border-b border-binance-border px-3 py-2">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-[10px] font-medium uppercase tracking-wider text-binance-text-muted transition-colors hover:text-binance-text-secondary"
        aria-expanded={open}
      >
        <span>Kalite</span>
        {open ? (
          <Minus className="h-3 w-3" />
        ) : (
          <Plus className="h-3 w-3" />
        )}
      </button>
      {open && (
        <>
          <ul className="mt-2 space-y-1">
            {QUALITY_ITEMS.map((item) => (
              <li
                key={item.label}
                className="flex items-center gap-2 text-[11px]"
              >
                <span
                  className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span
                  className="w-10 font-mono font-semibold"
                  style={{ color: item.color }}
                >
                  {item.label}
                </span>
                <span className="text-binance-text-secondary">
                  {item.desc}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-3 border-t border-binance-border/60 pt-2">
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
              Yön
            </div>
            <ul className="space-y-1">
              {DIRECTION_ITEMS.map((item) => (
                <li
                  key={item.label}
                  className="flex items-center gap-2 text-[11px]"
                >
                  <span
                    className="inline-block w-3 shrink-0 text-center font-bold leading-none"
                    style={{ color: item.color }}
                  >
                    {item.icon}
                  </span>
                  <span
                    className="w-10 font-mono font-semibold"
                    style={{ color: item.color }}
                  >
                    {item.label}
                  </span>
                  <span className="text-binance-text-secondary">
                    {item.desc}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
