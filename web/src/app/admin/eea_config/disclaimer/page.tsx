"use client";

import { LoadingAnimation } from "@/components/Loading";
import { AdminPageTitle } from "@/components/admin/Title";
import { fetcher } from "@/lib/fetcher";
import { Text, Title, Button } from "@tremor/react";
import { FiCpu } from "react-icons/fi";
import useSWR from "swr";
import { Form, Formik, Field } from "formik";
import { TextFormField } from "@/components/admin/connectors/Field";
import { usePopup } from "@/components/admin/connectors/Popup";

const GET_EEA_CONFIG_URL = "/api/eea_config/get_eea_config";
const SET_EEA_CONFIG_URL = "/api/eea_config/set_eea_config";

const Page = () => {
  const { data, isLoading, error } = useSWR<{ config: string }>(
    GET_EEA_CONFIG_URL,
    fetcher
  );
  let config_json = {"disclaimer":{"disclaimer_text":"", "disclaimer_title":""}};
  if (data){
    console.log(data)
    config_json = JSON.parse(data?.config);
  }

  const disclaimer_text = config_json?.disclaimer?.disclaimer_text || "";
  const disclaimer_title = config_json?.disclaimer?.disclaimer_title || "";
  const { popup, setPopup } = usePopup();
  
  if (isLoading) {
    return <LoadingAnimation text="Loading" />;
  }
  return (
    <>
      {popup}
      <div className="mx-auto container">
        <AdminPageTitle
          title="Customize configurations"
          icon={<FiCpu size={32} className="my-auto" />}
        />
        <Title className="mb-2 mt-6">Customize disclaimer:</Title>
        <Text className="mb-2">
          Disclaimer for search page (disabled if empty).
        </Text>
        <div className="border rounded-md border-border p-3">
          <Formik
            initialValues={{ disclaimer_title: disclaimer_title, disclaimer_text: disclaimer_text}}
            onSubmit={async ({ disclaimer_title, disclaimer_text }, formikHelpers) => {
              config_json.disclaimer = {
                disclaimer_title: disclaimer_title,
                disclaimer_text: disclaimer_text
              };
              const body = JSON.stringify({ config: JSON.stringify(config_json) });
              const response = await fetch(SET_EEA_CONFIG_URL, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: body,
              });
              console.log(response);
              if (!response?.ok) {
                setPopup({
                  message: `Error while updating disclaimer: ${response.status} - ${response.statusText}`,
                  type: "error",
                });
                return;
              } else {
                setPopup({ message: "Disclaimer updated", type: "success" });
                return;
              }
            }}
          >
            <Form>
              <TextFormField
                name="disclaimer_title"
                label="Disclaimer title:"
              />
              <TextFormField
                name="disclaimer_text"
                label="Disclaimer text:"
                isTextArea={true}
              />
              <div className="flex">
                <Button size="xs" type="submit" className="w-48 mx-auto">
                  Submit
                </Button>
              </div>
            </Form>
          </Formik>
        </div>
      </div>
    </>
  );
};

export default Page;
