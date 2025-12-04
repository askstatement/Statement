import Chat from "@/containers/chat";

export async function generateMetadata({ params }) {
  return {
    title: "Statement - Talk to Your Financial Data",
  }
}

export default function ChatPage() {
  return <Chat />
} 