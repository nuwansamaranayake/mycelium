/* SHELL: vendored from groundwork/webshell - edit there, not here. */
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mycelium — RAG that shows you what it refused to read",
  description:
    "Knowledge-base search where the ACL filter runs before retrieval scoring, every " +
    "answer carries citations and a deterministic freshness label, and an off-corpus " +
    "question gets an honest miss instead of a fluent guess.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
