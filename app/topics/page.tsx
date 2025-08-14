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

        {mounted && presentationMeta?.suggestedActions && presentationMeta.suggestedActions.length > 0 ? (
          presentationMeta.suggestedActions.map((s: any, idx: number) => (
            <section className="space-y-3" key={`topic-${idx}`}>
              <h2 className="text-xl font-medium">{s.title}</h2>
              <p className="text-muted-foreground">{s.label}</p>
            </section>
          ))
        ) : (
          <>
            <section className="space-y-3">
              <h2 className="text-xl font-medium">No topics yet</h2>
              <p className="text-muted-foreground">
                Drop a PDF presentation onto the chat to generate tailored topics.
              </p>
            </section>
          </>
        )}
      </div>
    </main>
  );
}


