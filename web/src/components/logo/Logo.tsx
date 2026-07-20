"use client";

import { useSettings } from "@/lib/settings/hooks";

import { EEAIcon } from "../EEA_Logo";

export function Logo({
  height,
  width,
  className,
  size = "default",
}: {
  height?: number;
  width?: number;
  className?: string;
  size?: "small" | "default" | "large" | "eea_large";
}) {
  const settings = useSettings();

  const sizeMap = {
    small: { height: 24, width: 22 },
    default: { height: 32, width: 30 },
    large: { height: 48, width: 45 },
    eea_large: { height: 48, width: 90 },
  };

  const { height: defaultHeight, width: defaultWidth } = sizeMap[size];
  height = height || defaultHeight;
  width = width || defaultWidth;

  if (
    !settings ||
    !settings.logoUrl
  ) {
    return (
      <div style={{ height, width }} className={className}>
        <EEAIcon
          size={height}
          className={`${className} dark:text-[#fff] text-[#000]`}
        />
      </div>
    );
  }

  return (
    <div
      style={{ height, width }}
      className={`flex-none relative ${className}`}
    >
      {/* TODO: figure out how to use Next Image here */}
      <img
        src={settings.logoUrl}
        alt="Logo"
        style={{ objectFit: "contain", height, width }}
      />
    </div>
  );
}
