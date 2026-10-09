import React from "react";
import { Composition, registerRoot } from "remotion";
import { Reel, reelFrames, FPS } from "./Reel.jsx";
import { Story, STORY_FRAMES } from "./Story.jsx";

const demoScenes = [
  { text: "Mariana Ximenes foi de **coque polido**", dur: 2.6 },
  { text: "Dá pra fazer **em casa**", dur: 2.2, style: "dark" },
  { cta: true, text: "Salva pra **próxima festa**", dur: 2.6 },
];

const Root = () => (
  <>
    <Composition
      id="Reel"
      component={Reel}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={reelFrames(demoScenes)}
      defaultProps={{ scenes: demoScenes }}
      calculateMetadata={({ props }) => ({ durationInFrames: reelFrames(props.scenes) })}
    />
    <Composition
      id="Story"
      component={Story}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={STORY_FRAMES}
      defaultProps={{ kicker: "Enquete", text: "Você usaria **coque polido**?", hint: "Vota aqui embaixo" }}
    />
  </>
);

registerRoot(Root);
