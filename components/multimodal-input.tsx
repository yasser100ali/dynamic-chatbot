"use client";

import type { Attachment, ChatRequestOptions, CreateMessage, Message } from "ai";
import { motion } from "framer-motion";
import type React from "react";
import {
  useRef,
  useEffect,
  useCallback,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { toast } from "sonner";
import { useLocalStorage, useSessionStorage, useWindowSize } from "usehooks-ts";

import { cn, sanitizeUIMessages } from "@/lib/utils";

import { ArrowUpIcon, StopIcon, CrossIcon } from "./icons";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";

const defaultSuggestedActions = [
  {
    title: "Upload a presentation (PDF)",
    label: "Drop your slides to create a tailored chatbot",
    action:
      "I just uploaded a presentation. Create a structured chatbot persona and UI topics based on it, then suggest 5 questions I could ask.",
  },
  {
    title: "Summarize the deck",
    label: "Key points, audience, and outcomes",
    action:
      "Give a concise summary of the uploaded deck: purpose, audience, 3-5 key takeaways, and suggested next steps.",
  },
  {
    title: "Create topics",
    label: "Generate browsable topics from slides",
    action:
      "Infer 6-8 short topics from the presentation and include one-sentence blurbs for each.",
  },
  {
    title: "Draft a system prompt",
    label: "Produce a high-quality system prompt",
    action:
      "Write a single, high-quality system prompt for a chatbot specialized in this deck. Keep it concise, safe, and structured.",
  },
  {
    title: "Q&A coach",
    label: "Ask clarifying questions",
    action:
      "Ask me 5 clarifying questions that would make the chatbot better at answering questions about this deck.",
  },
];

export function MultimodalInput({
  chatId,
  input,
  setInput,
  isLoading,
  stop,
  messages,
  setMessages,
  append,
  handleSubmit,
  className,
}: {
  chatId: string;
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  stop: () => void;
  messages: Array<Message>;
  setMessages: Dispatch<SetStateAction<Array<Message>>>;
  append: (
    message: Message | CreateMessage,
    chatRequestOptions?: ChatRequestOptions,
  ) => Promise<string | null | undefined>;
  handleSubmit: (
    event?: {
      preventDefault?: () => void;
    },
    chatRequestOptions?: ChatRequestOptions,
  ) => void;
  className?: string;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { width } = useWindowSize();
  const [isDragOver, setIsDragOver] = useState(false);
  const [attachments, setAttachments] = useState<Array<Attachment>>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (textareaRef.current) {
      adjustHeight();
    }
  }, []);

  const adjustHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight + 2}px`;
    }
  };

  const [localStorageInput, setLocalStorageInput] = useLocalStorage(
    "input",
    "",
  );

  const [presentationMeta, setPresentationMeta] = useSessionStorage<any | null>(
    "presentation_meta",
    null,
  );

  useEffect(() => {
    if (textareaRef.current) {
      const domValue = textareaRef.current.value;
      // Prefer DOM value over localStorage to handle hydration
      const finalValue = domValue || localStorageInput || "";
      setInput(finalValue);
      adjustHeight();
    }
    // Only run once after hydration
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    setLocalStorageInput(input);
  }, [input, setLocalStorageInput]);

  const handleInput = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(event.target.value);
    adjustHeight();
  };

  const submitForm = useCallback(() => {
    // If we have attachments, send them explicitly using append to ensure they are included
    if (attachments.length > 0) {
      void append({
        role: "user",
        content: input,
        experimental_attachments: attachments,
      });
    } else {
      handleSubmit(undefined, {});
    }
    setLocalStorageInput("");
    setAttachments([]);

    if (width && width > 768) {
      textareaRef.current?.focus();
    }
  }, [append, attachments, handleSubmit, input, setLocalStorageInput, width]);

  const fileToDataUrl = (file: File) =>
    new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const filesToAttachments = async (files: FileList) => {
    const pdfFiles = Array.from(files).filter((f) =>
      f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"),
    );

    const results: Array<Attachment> = [];
    for (const file of pdfFiles) {
      const url = await fileToDataUrl(file);
      results.push({ name: file.name, contentType: file.type || "application/pdf", url });
    }
    return results;
  };

  const analyzePresentation = async (pdfAttachment: Attachment) => {
    try {
      const res = await fetch("/api/presentation_meta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pdf_data_url: pdfAttachment.url, filename: pdfAttachment.name }),
      });
      if (!res.ok) return;
      const meta = await res.json();
      setPresentationMeta(meta);
    } catch (err) {
      // no-op; metadata is optional
    }
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const newAttachments = await filesToAttachments(files);
      setAttachments((prev) => [...prev, ...newAttachments]);
      if (newAttachments.length > 0) {
        void analyzePresentation(newAttachments[0]);
      }
    }
  };

  return (
    <div className="relative w-full flex flex-col gap-4">
      {messages.length === 0 && (
        <div className="grid sm:grid-cols-2 gap-2 w-full">
          {(((mounted && presentationMeta?.suggestedActions) as any) || defaultSuggestedActions).map((suggestedAction: any, index: number) => (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ delay: 0.05 * index }}
              key={`suggested-action-${suggestedAction.title}-${index}`}
              className="block"
            >
              <Button
                variant="ghost"
                onClick={async () => {
                  append({
                    role: "user",
                    content: suggestedAction.action,
                  });
                }}
                className="text-left border rounded-xl px-4 py-3.5 text-sm flex-1 gap-1 sm:flex-col w-full h-auto justify-start items-start bg-zinc-900/50 hover:bg-zinc-900/70"
              >
                <span className="font-medium">{suggestedAction.title}</span>
                <span className="text-muted-foreground">
                  {suggestedAction.label}
                </span>
              </Button>
            </motion.div>
          ))}
        </div>
      )}

      <div
        className={cn(
          "flex w-full flex-col gap-2 rounded-xl border bg-muted p-2 transition-colors",
          isDragOver && "bg-primary/20",
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 items-center">
            {attachments.map((a) => (
              <div key={a.url} className="text-xs text-zinc-400 border border-zinc-700 rounded px-2 py-1 inline-flex items-center gap-1">
                <span>{a.name}</span>
                <button
                  aria-label="Remove attachment"
                  className="opacity-70 hover:opacity-100"
                  onClick={(e) => {
                    e.preventDefault();
                    setAttachments([]);
                    setPresentationMeta(null);
                  }}
                >
                  <CrossIcon size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex w-full items-end gap-2">
          <Textarea
            ref={textareaRef}
            placeholder="Send a message..."
            value={input}
            onChange={handleInput}
            className={cn(
              "min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-xl !text-base bg-muted flex-1",
              className,
            )}
            rows={3}
            autoFocus
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();

                if (isLoading) {
                  toast.error("Please wait for the model to finish its response!");
                } else {
                  submitForm();
                }
              }
            }}
          />

          {isLoading ? (
            <Button
              className="rounded-full p-1.5 h-fit m-0.5 border dark:border-zinc-600"
              onClick={(event) => {
                event.preventDefault();
                stop();
                setMessages((messages) => sanitizeUIMessages(messages));
              }}
            >
              <StopIcon size={14} />
            </Button>
          ) : (
            <Button
              className="rounded-full p-1.5 h-fit m-0.5 border dark:border-zinc-600"
              onClick={(event) => {
                event.preventDefault();
                submitForm();
              }}
              disabled={input.length === 0 && attachments.length === 0}
            >
              <ArrowUpIcon size={14} />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
