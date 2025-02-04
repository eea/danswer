import { Logo } from "../EEA_Logo";
import Link from "next/link";

export default function AuthFlowContainer({
  children,
  authState,
}: {
  children: React.ReactNode;
  authState?: "signup" | "login";
}) {
  return (
    // <div className="flex flex-col items-center justify-center min-h-screen bg-background">
    //   <div className="w-full max-w-md bg-black pt-8 pb-4 px-8 mx-4 gap-y-4 bg-white flex items-center flex-col rounded-xl shadow-lg border border-bacgkround-100">
    //     <Logo width={92} height={70} />
    <div className="p-4 flex flex-col items-center justify-center min-h-screen bg-background">
      <div className="w-full max-w-md bg-black pt-8 pb-6 px-8 mx-4 gap-y-4 bg-white flex items-center flex-col rounded-xl shadow-lg border border-bacgkround-100">
        <Logo width={70} height={70} />
        {children}
      </div>
      {authState === "login" && (
        <div className="text-sm mt-4 text-center w-full text-neutral-900 font-medium mx-auto">
          Don&apos;t have an account?{" "}
          <Link
            href="/auth/signup"
            className=" underline transition-colors duration-200"
          >
            Create one
          </Link>
        </div>
      )}
      {authState === "signup" && (
        <div className="text-sm mt-4 text-center w-full text-neutral-800 font-medium mx-auto">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className=" underline transition-colors duration-200"
          >
            Log In
          </Link>
        </div>
      )}
    </div>
  );
}
