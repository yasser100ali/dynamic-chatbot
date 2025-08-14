"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useSessionStorage } from "usehooks-ts";
import { useEffect, useState } from "react";

import { MessageIcon, SparklesIcon } from "./icons";

export const Overview = () => {
  const [presentationMeta] = useSessionStorage<any | null>(
    "presentation_meta",
    null,
  );
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return (
    <motion.div
      key="overview"
      className="max-w-3xl mx-auto md:mt-20"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ delay: 0.5 }}
    >
      <div className="rounded-xl p-6 flex flex-col gap-6 leading-relaxed text-center max-w-xl bg-zinc-900/50 border border-border/50">
        <p className="flex flex-row justify-center gap-3 items-center text-xl font-semibold">
          <SparklesIcon size={18} />
          <span>{mounted && presentationMeta?.title ? presentationMeta.title : "Educational Chatbot Builder"}</span>
          <MessageIcon size={18} />
        </p>
        <p className="text-muted-foreground">
          {mounted && presentationMeta?.description
            ? presentationMeta.description
            : "Upload a presentation to instantly tailor a chatbot and UI to that content. Or start chatting to get help designing one."}
        </p>
        <p className="text-xs text-muted-foreground">
          This copilot provides educational, non-diagnostic information. It does not replace professional clinical judgment.
        </p>
        <div>
          <Link
            className="font-medium underline underline-offset-4"
            href="/topics"
          >
            {mounted && presentationMeta?.title ? "Browse Presentation Topics →" : "Browse Topics →"}
          </Link>
        </div>
      </div>
    </motion.div>
  );
};
