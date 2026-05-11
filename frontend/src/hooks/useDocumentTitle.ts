import { useEffect } from "react";

/**
 * Browser tab title'ını "MarketLens — {pageName}" formatında günceller.
 */
export function useDocumentTitle(pageName: string): void {
  useEffect(() => {
    const previous = document.title;
    document.title = `MarketLens — ${pageName}`;
    return () => {
      document.title = previous;
    };
  }, [pageName]);
}
