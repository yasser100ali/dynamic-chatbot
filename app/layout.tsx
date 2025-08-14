import "./globals.css";
import { GeistSans } from "geist/font/sans";
import { Toaster } from "sonner";
import { cn } from "@/lib/utils";

export const metadata = {
  title: "Kaiser Healthcare AI Copilot",
  description:
    "Ask an expert about AI in healthcare: operations, early diagnosis, agents, RLHF, safety, and the dawn of superintelligence.",
  openGraph: {
    images: [
      {
        url: "/og?title=Kaiser Healthcare AI Copilot",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: [
      {
        url: "/og?title=Kaiser Healthcare AI Copilot",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head></head>
      <body className={cn(GeistSans.className, "antialiased dark")}> 
        <Toaster position="top-center" richColors />
        {children}
      </body>
    </html>
  );
}
