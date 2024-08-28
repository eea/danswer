import { redirect } from "next/navigation";
import { unstable_noStore as noStore } from "next/cache";
import { InstantSSRAutoRefresh } from "@/components/SSRAutoRefresh";
import { WelcomeModal } from "@/components/initialSetup/welcome/WelcomeModalWrapper";
import { ApiKeyModal } from "@/components/llm/ApiKeyModal";
import { ChatProvider } from "@/components/context/ChatContext";
import { fetchChatData } from "@/lib/chat/fetchChatData";
import { fetchEEASettings } from "@/lib/eea/fetchEEASettings";
import { UserDisclaimerModal } from "@/components/search/UserDisclaimerModal";
import WrappedChat from "./WrappedChat";

export default async function Page({
  searchParams,
}: {
  searchParams: { [key: string]: string };
}) {
  noStore();

  const data = await fetchChatData(searchParams);


  if ("redirect" in data) {
    redirect(data.redirect);
  }
 
  const config = await fetchEEASettings();
  
  const {
    disclaimerTitle,
    disclaimerText
  } = config;
  
  const {
    user,
    chatSessions,
    ccPairs,
    availableSources,
    documentSets,
    assistants,
    tags,
    llmProviders,
    folders,
    toggleSidebar,
    openedFolders,
    defaultAssistantId,
    finalDocumentSidebarInitialWidth,
    shouldShowWelcomeModal,
    shouldDisplaySourcesIncompleteModal,
    userInputPrompts,
  } = data;

  return (
    <>
      <UserDisclaimerModal disclaimerText={disclaimerText} disclaimerTitle={disclaimerTitle}/>

      <InstantSSRAutoRefresh />
      {shouldShowWelcomeModal && <WelcomeModal user={user} />}
      {!shouldShowWelcomeModal && !shouldDisplaySourcesIncompleteModal && (
        <ApiKeyModal user={user} />
      )}
      <ChatProvider
        value={{
          chatSessions,
          availableSources,
          availableDocumentSets: documentSets,
          availableAssistants: assistants,
          availableTags: tags,
          llmProviders,
          folders,
          openedFolders,
          userInputPrompts,
          }}
      >

        <WrappedChat
          defaultAssistantId={defaultAssistantId}
          initiallyToggled={toggleSidebar}
        />
      </ChatProvider>
    </>
  );
}
