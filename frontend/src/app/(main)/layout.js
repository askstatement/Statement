'use client'
import "@/style/layout/external.scss"
import "@/style/globals.scss";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";

export default function RootLayout({ children }) {
  return (
    <div className="external_layout">
        <Header />
        <div className="page_content">{children}</div>
        <Footer />
    </div>
  );
}
