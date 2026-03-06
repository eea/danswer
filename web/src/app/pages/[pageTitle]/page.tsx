import { unstable_noStore as noStore } from "next/cache";
import { getCurrentUserSS } from "@/lib/userSS";
import { User } from "@/lib/types";
import { HealthCheckBanner } from "@/components/health/healthcheck";
import { notFound } from "next/navigation";
import { fetchEEASettings } from "@/lib/eea/fetchEEASettings";
import BackButton from "@/refresh-components/buttons/BackButton";

export default async function Page(props: {
    params: Promise<{ pageTitle: string }>;
}) {
    const params = await props.params;

    noStore();
    const pageTitle = params.pageTitle;

    let currentUser: User | null = null;
    try {
        currentUser = await getCurrentUserSS();
    } catch (e) {
        console.log(`Some fetch failed for the custom page - ${e}`);
    }

    const config = await fetchEEASettings();
    const { eea_config } = config;

    let pageContent = eea_config?.pages?.[pageTitle];
    if (!pageContent) {
        return notFound();
    }

    return (
        <>
            <div className="m-3">
                <HealthCheckBanner />
            </div>
            <div className="mx-auto max-w-4xl px-4 py-8">
                <div className="mb-8">
                    <BackButton routerOverride="/app" />
                </div>

                <div className="prose prose-slate max-w-none">
                    <div dangerouslySetInnerHTML={{ __html: pageContent }} />
                </div>
            </div>
        </>
    );
}
