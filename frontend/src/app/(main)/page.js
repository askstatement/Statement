import Home from "@/containers/home";
import "@/style/container/home.scss"

export async function generateMetadata({ params }) {
  return {
      title: "Statement - Talk to Your Financial Data",
  }
}


export default function HomePage() {
  return <Home/>;
}
