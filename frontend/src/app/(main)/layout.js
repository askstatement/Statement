'use client'
import "@/style/layout/external.scss"
import "@/style/globals.scss";

export default function RootLayout({ children }) {
  return (
    <div className="external_layout">
        <div className="page_content">{children}</div>
    </div>
  );
}
