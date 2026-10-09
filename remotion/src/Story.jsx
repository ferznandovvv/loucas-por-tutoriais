import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Fonts, Headline, HandleChip, PhotoBg, PINK, INK, OFF } from "./common.jsx";

export const STORY_FRAMES = 150; // 5 s

const Kicker = ({ text, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delay, fps, config: { damping: 12 } });
  return (
    <div
      style={{
        display: "inline-block",
        background: PINK,
        color: "#fff",
        fontFamily: "Oswald",
        fontWeight: 700,
        fontSize: 40,
        letterSpacing: 2,
        textTransform: "uppercase",
        padding: "8px 26px",
        borderRadius: 999,
        transform: `scale(${p})`,
      }}
    >
      {text}
    </div>
  );
};

const Hint = ({ text, color, delay = 20 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bob = Math.sin(frame / 6) * 6;
  return (
    <div style={{ fontFamily: "Liberation", fontWeight: 700, fontSize: 38, color, opacity: o, transform: `translateY(${bob}px)` }}>
      {text}
    </div>
  );
};

/** Moldura tracejada que marca onde colar o adesivo (some no PNG final se "guide" for false). */
const StickerZone = ({ top, height, color, guide }) =>
  guide ? (
    <div style={{ position: "absolute", left: 140, right: 140, top, height, border: `4px dashed ${color}`, borderRadius: 40, opacity: 0.35 }} />
  ) : null;

export const Story = ({ kicker, text, hint, photo, style, card, guide = false }) => {
  const frame = useCurrentFrame();
  const dark = !!photo || style === "dark" || !!card;
  const fg = dark ? "#fff" : INK;

  // "Post novo": capa do carrossel num cartao inclinado
  if (card) {
    const { fps } = useVideoConfig();
    const p = spring({ frame: frame - 6, fps, config: { damping: 13 } });
    return (
      <AbsoluteFill style={{ background: INK }}>
        <Fonts />
        <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 60%, rgba(226,32,98,.45), rgba(0,0,0,0) 60%)" }} />
        <div style={{ position: "absolute", top: 260, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 30, padding: "0 80px" }}>
          <Kicker text={kicker} />
          <Headline text={text} size={88} delay={4} />
        </div>
        <div
          style={{
            position: "absolute",
            left: 190,
            top: 760,
            width: 700,
            height: 875,
            borderRadius: 30,
            overflow: "hidden",
            boxShadow: "0 40px 100px rgba(0,0,0,.6)",
            transform: `translateY(${(1 - p) * 300}px) rotate(${-4 * p}deg)`,
            opacity: p,
          }}
        >
          <Img src={staticFile(card)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
        <div style={{ position: "absolute", bottom: 150, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <Hint text={hint} color="#fff" />
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ background: photo ? "#000" : style === "dark" ? INK : OFF }}>
      <Fonts />
      {photo ? (
        <>
          <PhotoBg photo={photo} progress={frame / STORY_FRAMES} />
          <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,.5) 0%, rgba(0,0,0,0) 18%, rgba(0,0,0,0) 48%, rgba(0,0,0,.9) 74%, rgba(0,0,0,.95) 100%)" }} />
          <div style={{ position: "absolute", top: 120, left: 60 }}>
            <HandleChip />
          </div>
          <StickerZone top={720} height={420} color="#fff" guide={guide} />
          <div style={{ position: "absolute", left: 70, right: 70, bottom: 300, display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
            <Kicker text={kicker} />
            <Headline text={text} size={92} delay={4} />
            <Hint text={hint} color="#fff" />
          </div>
        </>
      ) : (
        <>
          <AbsoluteFill
            style={{
              background: `radial-gradient(circle at ${25 + 30 * (frame / STORY_FRAMES)}% 20%, rgba(226,32,98,${style === "dark" ? 0.4 : 0.22}), rgba(0,0,0,0) 55%)`,
            }}
          />
          <div style={{ position: "absolute", top: 120, left: 60 }}>
            <HandleChip dark={style === "dark"} />
          </div>
          <div style={{ position: "absolute", left: 70, right: 70, top: 330, display: "flex", flexDirection: "column", alignItems: "center", gap: 30 }}>
            <Kicker text={kicker} />
            <Headline text={text} size={100} delay={4} color={fg} />
            <Hint text={hint} color={style === "dark" ? "#fff" : PINK} />
          </div>
          <StickerZone top={1060} height={520} color={fg} guide={guide} />
        </>
      )}
    </AbsoluteFill>
  );
};
