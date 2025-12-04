import Login from "@/containers/login";

export async function generateMetadata({ params }) {
  return {
      title: "Statement - Talk to Your Financial Data",
  }
}

export default function LoginPage () {
    return <Login/>
}