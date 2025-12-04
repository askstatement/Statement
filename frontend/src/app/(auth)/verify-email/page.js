import VerifyEmail from "@/containers/verify-email";

export async function generateMetadata({ params }) {
  return {
      title: "Statement - Talk to Your Financial Data",
  }
}

export default function EmailVeryfication () {
    return <VerifyEmail/>
}