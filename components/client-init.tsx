"use client";

import { useEffect } from "react";

export function ClientInitReset() {
  useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("presentation_meta");
      }
    } catch {}
  }, []);
  return null;
}


