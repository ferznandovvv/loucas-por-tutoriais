import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Fonts, Headline, HandleChip, PhotoBg, Avatar, Verified, PINK, INK, OFF, NAME, HANDLE } from "./common.jsx";

export const FPS = 30;
export const reelFrames = (scenes) => scenes.reduce((a, s) => a + Math.round((s.dur ?? 2.6) * FPS), 0);

const Scene = ({ s, frames, last }) => {
  const frame = useCurrentFrame();
  const progress = frame / frames;
  const enter = interpolate(frame, [0, 7], [0, 1], { extrapolateRight: "clamp" });
  const exit = last ? 1 : interpolate(frame, [frames - 5, frames], [1, 0], { extrapolateLeft: "clamp" });
  const dark = !!s.photo || s.style === "dark";
  const bg = s.photo ? "#000" : s.style === "dark" ? INK : OFF;
  const textColor = dark ? "#fff" : INK;

  if (s.cta) {
    return (
      <AbsoluteFill style={{ background: INK, opacity: enter }}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 56, padding: "0 70px" }}>
          <div style={{ transform: `scale(${interpolate(frame, [0, 12], [0.6, 1], { extrapolateRight: "clamp" })})` }}>
            <Avatar size={220} ring={8} />
          </div>
          <div style={{ fontFamily: "Liberation", fontWeight: 700, fontSize: 44, color: "#fff", display: "flex", gap: 12, alignItems: "center" }}>
            {NAME} <Verified size={40} />
          </div>
          <Headline text={s.text} size={100} delay={6} />
          {s.sub ? (
            <div style={{ fontFamily: "Liberation", fontSize: 40, color: "#ddd", opacity: interpolate(frame, [18, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{s.sub}</div>
          ) : null}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ background: bg, opacity: Math.min(enter, exit) }}>
      {s.photo ? (
        <>
          <PhotoBg photo={s.photo} progress={progress} />
          <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,.45) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 45%, rgba(0,0,0,.88) 78%, rgba(0,0,0,.92) 100%)" }} />
        </>
      ) : s.style === "dark" ? (
        <AbsoluteFill style={{ background: `radial-gradient(circle at ${30 + 40 * progress}% 35%, rgba(226,32,98,.35), rgba(0,0,0,0) 55%)` }} />
      ) : (
        <AbsoluteFill style={{ background: `radial-gradient(circle at ${70 - 40 * progress}% 30%, rgba(226,32,98,.18), rgba(0,0,0,0) 60%)` }} />
      )}
      <AbsoluteFill
        style={{
          justifyContent: s.photo && s.photo.mode !== "card" ? "flex-end" : s.photo ? "flex-end" : "center",
          alignItems: "center",
          padding: s.photo ? "0 70px 430px" : "0 70px 120px",
        }}
      >
        <Headline text={s.text} size={s.size ?? (s.photo ? 96 : 112)} color={textColor} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Reel = ({ scenes }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  let from = 0;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Fonts />
      {scenes.map((s, i) => {
        const frames = Math.round((s.dur ?? 2.6) * FPS);
        const el = (
          <Sequence key={i} from={from} durationInFrames={frames}>
            <Scene s={s} frames={frames} last={i === scenes.length - 1} />
          </Sequence>
        );
        from += frames;
        return el;
      })}
      {/* barra de progresso */}
      <div style={{ position: "absolute", top: 0, left: 0, height: 12, width: `${(frame / durationInFrames) * 100}%`, background: PINK }} />
      {/* perfil fixo no alto (abaixo da area do cabecalho do Instagram) */}
      <div style={{ position: "absolute", top: 190, left: 60, opacity: scenes[Math.min(scenes.length - 1, 0)] ? 1 : 0 }}>
        <HandleChip />
      </div>
    </AbsoluteFill>
  );
};
