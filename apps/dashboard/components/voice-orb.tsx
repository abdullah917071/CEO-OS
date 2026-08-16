"use client";

import { useEffect, useRef } from "react";

interface VoiceOrbProps {
  state: "idle" | "listening" | "thinking" | "speaking";
  size?: number;
}

export function VoiceOrb({ state, size = 80 }: VoiceOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const phaseRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const centerX = size / 2;
    const centerY = size / 2;
    const baseRadius = size * 0.28;

    const colors = {
      idle: ["#1e40af", "#3b82f6", "#60a5fa"],
      listening: ["#dc2626", "#ef4444", "#f87171"],
      thinking: ["#7c3aed", "#8b5cf6", "#a78bfa"],
      speaking: ["#059669", "#10b981", "#34d399"],
    };

    function animate() {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, size, size);
      phaseRef.current += 0.04;
      const phase = phaseRef.current;

      const stateColors = colors[state];
      const pulseScale = state === "idle" ? 0 : state === "listening" ? 0.18 : state === "thinking" ? 0.12 : 0.22;
      const pulseRadius = baseRadius + Math.sin(phase * 2) * baseRadius * pulseScale;

      // Outer glow ring
      const outerGlow = ctx.createRadialGradient(centerX, centerY, pulseRadius * 0.6, centerX, centerY, pulseRadius * 1.8);
      outerGlow.addColorStop(0, `${stateColors[1]}30`);
      outerGlow.addColorStop(1, "transparent");
      ctx.beginPath();
      ctx.arc(centerX, centerY, pulseRadius * 1.8, 0, Math.PI * 2);
      ctx.fillStyle = outerGlow;
      ctx.fill();

      // Wave rings (3 concentric, animated)
      for (let i = 0; i < 3; i++) {
        const ringRadius = pulseRadius * (0.65 + i * 0.18) + Math.sin(phase + i * 1.2) * 3;
        const alpha = state === "idle" ? 0.15 - i * 0.04 : 0.4 - i * 0.1;
        ctx.beginPath();
        ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `${stateColors[i]}${Math.round(alpha * 255).toString(16).padStart(2, "0")}`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Core orb
      const gradient = ctx.createRadialGradient(
        centerX - pulseRadius * 0.25,
        centerY - pulseRadius * 0.25,
        0,
        centerX,
        centerY,
        pulseRadius
      );
      gradient.addColorStop(0, stateColors[2]);
      gradient.addColorStop(0.5, stateColors[1]);
      gradient.addColorStop(1, stateColors[0]);

      ctx.beginPath();
      ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Inner highlight
      const highlight = ctx.createRadialGradient(
        centerX - pulseRadius * 0.3,
        centerY - pulseRadius * 0.3,
        0,
        centerX,
        centerY,
        pulseRadius * 0.8
      );
      highlight.addColorStop(0, "rgba(255,255,255,0.35)");
      highlight.addColorStop(1, "transparent");
      ctx.beginPath();
      ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
      ctx.fillStyle = highlight;
      ctx.fill();

      // Waveform bars for listening/speaking states
      if (state === "listening" || state === "speaking") {
        const barCount = 7;
        const barWidth = pulseRadius * 0.12;
        const maxBarH = pulseRadius * 0.55;
        const startX = centerX - (barCount * barWidth * 1.4) / 2;

        for (let i = 0; i < barCount; i++) {
          const barH = maxBarH * (0.3 + 0.7 * Math.abs(Math.sin(phase * 3 + i * 0.7)));
          const barX = startX + i * barWidth * 1.4;
          const barY = centerY - barH / 2;

          ctx.fillStyle = "rgba(255,255,255,0.75)";
          ctx.beginPath();
          ctx.roundRect(barX, barY, barWidth, barH, barWidth / 2);
          ctx.fill();
        }
      }

      // Thinking spinner arc
      if (state === "thinking") {
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(phase * 2);
        ctx.beginPath();
        ctx.arc(0, 0, pulseRadius * 1.25, 0, Math.PI * 1.5);
        ctx.strokeStyle = stateColors[2];
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.stroke();
        ctx.restore();
      }

      animRef.current = requestAnimationFrame(animate);
    }

    animate();
    return () => cancelAnimationFrame(animRef.current);
  }, [state, size]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: size, height: size }}
      className="select-none"
      aria-label={`Voice assistant state: ${state}`}
    />
  );
}
