import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export const PINK = "#E22062";
export const INK = "#141214";
export const OFF = "#F7F1EC";
export const HANDLE = "@loucasportutoriais";
export const NAME = "Loucas por Tutoriais";

export const Fonts = () => (
  <style>{`
    @font-face { font-family: 'Oswald'; src: url('${staticFile("fonts/Oswald.ttf")}') format('truetype'); font-weight: 200 700; }
    @font-face { font-family: 'Liberation'; src: url('${staticFile("fonts/LiberationSans-Regular.ttf")}') format('truetype'); font-weight: 400; }
    @font-face { font-family: 'Liberation'; src: url('${staticFile("fonts/LiberationSans-Bold.ttf")}') format('truetype'); font-weight: 700; }
  `}</style>
);

// "texto com **destaque**" -> [{text, hl}]
export const segments = (text) => {
  const segs = text
    .split(/(\*\*[^*]+\*\*)/)
    .filter(Boolean)
    .map((p) => ({ text: p.replace(/\*\*/g, ""), hl: p.startsWith("**") }));
  // pontuacao logo depois de um destaque ("**coragem**?") gruda na palavra anterior para nao quebrar sozinha na linha
  for (let i = 1; i < segs.length; i++) {
    const m = segs[i].text.match(/^[.,!?:;]+/);
    if (m) {
      segs[i - 1].text += m[0];
      segs[i].text = segs[i].text.slice(m[0].length);
    }
  }
  return segs.filter((s) => s.text.trim().length);
};

/** Manchete condensada em caixa alta, palavras entram uma a uma, destaque com tarja rosa que se desenha. */
export const Headline = ({ text, size = 104, delay = 0, align = "center", color = "#fff", maxWidth = 940 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  let idx = 0;
  const segs = segments(text);
  return (
    <div
      style={{
        fontFamily: "Oswald",
        fontWeight: 700,
        fontSize: size,
        lineHeight: 1.22,
        textTransform: "uppercase",
        color,
        textAlign: align,
        maxWidth,
        letterSpacing: 0.5,
      }}
    >
      {segs.map((s, si) => {
        const words = s.text.split(/\s+/).filter(Boolean);
        const start = idx;
        idx += words.length;
        const hlProgress = s.hl
          ? interpolate(frame - delay - start * 3 - 4, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          : 0;
        const inner = words.map((w, wi) => {
          const f = frame - delay - (start + wi) * 3;
          const p = spring({ frame: f, fps, config: { damping: 14, stiffness: 160 } });
          return (
            <span
              key={wi}
              style={{
                display: "inline-block",
                opacity: interpolate(f, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                transform: `translateY(${(1 - p) * 40}px) scale(${0.9 + 0.1 * p})`,
                marginRight: wi < words.length - 1 ? "0.24em" : 0,
              }}
            >
              {w}
            </span>
          );
        });
        const lead = si > 0 && !/^[.,!?:;]/.test(s.text) ? " " : "";
        return (
          <React.Fragment key={si}>
            {lead}
            <span
              style={
                s.hl
                  ? {
                      backgroundImage: `linear-gradient(${PINK}, ${PINK})`,
                      backgroundRepeat: "no-repeat",
                      backgroundSize: `${hlProgress * 100}% 100%`,
                      boxDecorationBreak: "clone",
                      WebkitBoxDecorationBreak: "clone",
                      padding: "0 0.14em",
                      color: "#fff",
                    }
                  : {}
              }
            >
              {inner}
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
};

/** Texto corrido com **negrito** (estilo post). */
export const Rich = ({ text, size = 40, color = "#fff", weight = 400, align = "center" }) => (
  <div style={{ fontFamily: "Liberation", fontSize: size, color, fontWeight: weight, textAlign: align, lineHeight: 1.3 }}>
    {segments(text).map((s, i) => (
      <span key={i} style={{ fontWeight: s.hl ? 700 : weight }}>
        {s.text}
      </span>
    ))}
  </div>
);

export const Avatar = ({ size = 64, ring = 0 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      overflow: "hidden",
      border: ring ? `${ring}px solid #fff` : "none",
      flexShrink: 0,
    }}
  >
    <Img src={staticFile("avatar.png")} style={{ width: "116%", height: "116%", margin: "-8% 0 0 -8%", objectFit: "cover" }} />
  </div>
);

export const Verified = ({ size = 34 }) => (
  <svg width={size} height={size} viewBox="0 0 40 40">
    <path
      fill="#1D9BF0"
      d="M20 1.5l4.1 3 5-.6 2 4.6 4.6 2-.6 5 3 4.1-3 4.1.6 5-4.6 2-2 4.6-5-.6-4.1 3-4.1-3-5 .6-2-4.6-4.6-2 .6-5-3-4.1 3-4.1-.6-5 4.6-2 2-4.6 5 .6z"
    />
    <path d="M12.5 20.5l5 5 10-11" stroke="#fff" strokeWidth="3.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const HandleChip = ({ dark = true }) => (
  <div style={{ display: "inline-flex", alignItems: "center", gap: 14, padding: "6px 22px 6px 6px", borderRadius: 999, background: dark ? "rgba(0,0,0,.35)" : "rgba(255,255,255,.6)" }}>
    <Avatar size={58} />
    <div style={{ fontFamily: "Liberation", fontWeight: 700, fontSize: 30, color: dark ? "#fff" : INK, display: "flex", alignItems: "center", gap: 8 }}>
      {HANDLE}
      <Verified size={30} />
    </div>
  </div>
);

/** Foto de fundo: "cover" ocupa a tela com zoom lento; "card" mostra a foto num cartao sobre a mesma foto desfocada. */
export const PhotoBg = ({ photo, progress = 0, height = 1920 }) => {
  if (!photo) return null;
  const src = staticFile(photo.src);
  const pos = `${(photo.focus ?? 0.5) * 100}% ${(photo.focusY ?? 0.4) * 100}%`;
  if (photo.mode === "card") {
    const z = photo.zoom ?? 1;
    return (
      <div style={{ position: "absolute", inset: 0, background: "#000" }}>
        <Img src={src} style={{ position: "absolute", inset: -60, width: "calc(100% + 120px)", height: "calc(100% + 120px)", objectFit: "cover", objectPosition: pos, filter: "blur(38px) brightness(0.55)" }} />
        <div
          style={{
            position: "absolute",
            left: 90,
            top: photo.cardTop ?? 300,
            width: 900,
            height: photo.cardH ?? 900,
            borderRadius: 36,
            overflow: "hidden",
            boxShadow: "0 30px 80px rgba(0,0,0,.5)",
            transform: `scale(${1.04 - 0.04 * progress})`,
          }}
        >
          <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transform: `scale(${z})`, transformOrigin: pos }} />
        </div>
      </div>
    );
  }
  return (
    <Img
      src={src}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height,
        objectFit: "cover",
        objectPosition: pos,
        transform: `scale(${(photo.zoom ?? 1) * (1.12 - 0.12 * progress)})`,
        transformOrigin: pos,
      }}
    />
  );
};
