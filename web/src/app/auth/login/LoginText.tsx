"use client";

import React, { useContext } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";
import Text from "@/refresh-components/texts/Text";

export default function LoginText() {
  const settings = useContext(SettingsContext);
  return (
    <div className="w-full flex flex-col ">
      <Text as="p" headingH2 text05>
        Log In to{" "}
        {(settings && settings?.enterpriseSettings?.application_name) ||
          "AI Hub"}
      </Text>
    </div>
  );
}
