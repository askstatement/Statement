import ResetPasswordPage from "@/containers/reset-password";

export async function generateMetadata({ params }) {
  return {
      title: "Statement - Talk to Your Financial Data",
  }
}

export default function ResetPassword () {
    return <ResetPasswordPage/>
}