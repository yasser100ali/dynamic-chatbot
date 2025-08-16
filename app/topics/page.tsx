"use client";

import { useSessionStorage } from "usehooks-ts";
import { useEffect, useState } from "react";

export default function TopicsPage() {
  const [presentationMeta] = useSessionStorage<any | null>(
    "presentation_meta",
    null,
  );
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return (
    <main className="min-h-screen px-4 py-10 flex justify-center">
      <div className="max-w-3xl w-full space-y-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">
            {mounted && presentationMeta?.title ? presentationMeta.title : "Upload a presentation to tailor topics"}
          </h1>
          <p className="text-muted-foreground">
            {mounted && presentationMeta?.description
              ? presentationMeta.description
              : "After uploading, this page will show topics inferred from your slides."}
          </p>
        </header>

        {mounted && presentationMeta?.topics && presentationMeta.topics.length > 0 ? (
          <section className="space-y-3">
            <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
              {presentationMeta.topics.map((t: string, idx: number) => (
                <li key={`t-${idx}`}>{t}</li>
              ))}
            </ul>
          </section>
        ) : (
          <section className="space-y-3">
            <h2 className="text-xl font-medium">No topics yet</h2>
            <p className="text-muted-foreground">
              Drop a PDF presentation onto the chat to generate tailored topics.
            </p>
          </section>
        )}

        {mounted && presentationMeta?.suggestedActions && presentationMeta.suggestedActions.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-xl font-medium">Suggested Actions</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {presentationMeta.suggestedActions.map((s: any, idx: number) => (
                <div key={`sa-${idx}`} className="rounded-xl border bg-zinc-900/50 px-4 py-3">
                  <div className="font-medium">{s.title}</div>
                  <div className="text-muted-foreground text-sm">{s.label}</div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}


