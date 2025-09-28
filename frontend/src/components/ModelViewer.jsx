// src/components/ModelViewer.jsx
import { Suspense, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, useGLTF, Center } from "@react-three/drei";

function Model() {
  const { scene } = useGLTF("/models/boxing_gloves/scene.gltf");
  const ref = useRef();

  // Rotate around Y axis
  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.5;
    }
  });

  return (
    <group ref={ref}>
      {/* <Center> ensures pivot is at center */}
      <Center>
        {/* ⬆️ Increased scale from 2.2 → 3 */}
        <primitive object={scene} scale={3} />
      </Center>
    </group>
  );
}

export default function ModelViewer() {
  return (
    <div style={{ width: "100%", height: "320px", marginTop: "1.5rem" }}>
      <Canvas
        // ⬇️ Camera closer & tighter FOV for a smaller/tighter scene
        camera={{ position: [0, 1.2, 3], fov: 35 }}
        gl={{ alpha: true, antialias: true }}
        onCreated={({ gl }) => {
          gl.setClearAlpha(0);
          gl.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        }}
      >
        <hemisphereLight intensity={0.9} />
        <directionalLight position={[3, 5, 3]} intensity={1.4} />

        <Suspense fallback={null}>
          <Model />
          <Environment preset="city" />
        </Suspense>

        <OrbitControls enableZoom={false} enablePan={false} />
      </Canvas>
    </div>
  );
}
