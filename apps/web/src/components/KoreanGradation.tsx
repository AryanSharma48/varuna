import React, { useEffect, useRef } from 'react';

export interface GradientParams {
  mode: string;
  colors: Array<{
    id: string;
    hex: string;
    pos: number;
    name: string;
  }>;
  angle: number;
  centerX: number;
  centerY: number;
  scale: number;
  softness: number;
  wave: number;
  distortion: number;
  grain: number;
  vignette: number;
  count: number;
  fade: number;
  envelope: string;
  spread: number;
  soften: number;
  pixelCols: number;
  pixelRows: number;
  pixelAngle: number;
  pixelDither: number;
  pixelGap: number;
  archBase: number;
  archHeight: number;
  archWidth: number;
  archGlow: number;
  archEdge: number;
  animated: boolean;
  speed: number;
  motionAmount: number;
  motionReverse: boolean;
  seed: number;
  backdrop: string;
}

export const DEFAULT_GRADATION_PARAMS: GradientParams = {
  mode: "stripes",
  colors: [
    { id: "c997_53717", hex: "#FFFFFF", pos: 18, name: "White" },
    { id: "c998_89478", hex: "#78B8F9", pos: 57, name: "Sky blue" },
    { id: "c999_25239", hex: "#5667FF", pos: 60, name: "Ultramarine" },
    { id: "c1000_61000", hex: "#4D2FF9", pos: 100, name: "Iris" }
  ],
  angle: 32,
  centerX: 50,
  centerY: 50,
  scale: 68,
  softness: 24,
  wave: 14,
  distortion: 28,
  grain: 42,
  vignette: 0,
  count: 6,
  fade: 40,
  envelope: "ramp",
  spread: -20,
  soften: 0,
  pixelCols: 16,
  pixelRows: 10,
  pixelAngle: 45,
  pixelDither: 50,
  pixelGap: 0,
  archBase: 70,
  archHeight: 50,
  archWidth: 100,
  archGlow: 55,
  archEdge: 30,
  animated: true,
  speed: 100,
  motionAmount: 0.0,
  motionReverse: false,
  seed: 174074637,
  backdrop: "#0B1220"
};

interface KoreanGradationProps {
  className?: string;
  style?: React.CSSProperties;
  params?: Partial<GradientParams>;
  children?: React.ReactNode;
}

export const KoreanGradation: React.FC<KoreanGradationProps> = ({
  className = '',
  style = {},
  params: customParams,
  children
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(performance.now());

  const config = { ...DEFAULT_GRADATION_PARAMS, ...customParams };

  // Convert HEX to RGB floats [0..1]
  const hexToRgb = (hex: string): [number, number, number] => {
    const clean = hex.replace('#', '');
    const num = parseInt(clean, 16);
    return [
      ((num >> 16) & 255) / 255.0,
      ((num >> 8) & 255) / 255.0,
      (num & 255) / 255.0
    ];
  };

  const rgbColors = config.colors.map(c => hexToRgb(c.hex));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl', { 
      alpha: false, 
      antialias: true,
      powerPreference: 'high-performance' 
    });

    if (!gl) {
      console.warn('WebGL unavailable, falling back to 2D canvas context');
      return;
    }

    // Vertex Shader: Fullscreen quad
    const vsSource = `
      attribute vec2 a_position;
      varying vec2 v_uv;
      void main() {
        v_uv = (a_position + 1.0) * 0.5;
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `;

    // Fragment Shader: High-precision Ribbon Field gradient with wave and grain
    const fsSource = `
      precision highp float;
      varying vec2 v_uv;
      
      uniform vec2 u_resolution;
      uniform vec2 u_center;
      uniform float u_scale;
      uniform float u_angle;
      uniform float u_wave;
      uniform float u_wave_clock;
      uniform float u_grain;
      
      uniform vec3 u_color0;
      uniform vec3 u_color1;
      uniform vec3 u_color2;
      uniform vec3 u_color3;

      // Pseudo-random noise for analog film grain
      float pseudoNoise(vec2 co) {
        return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453);
      }

      // Smoothstep interpolation between two stops
      vec3 sampleStripeField(float p) {
        // Stops derived from Ribbon Field parameters (pos: 18, 57, 60, 100 with softness 24):
        // White: 4.32% to 33.18%
        // Sky Blue: 37.86% to 58.14%
        // Ultramarine: 58.86% to 79.64%
        // Iris: 80.00% to 100.00%
        
        float s0 = 0.0432;
        float s1 = 0.3318;
        float s2 = 0.3786;
        float s3 = 0.5814;
        float s4 = 0.5886;
        float s5 = 0.7964;
        float s6 = 0.8000;
        float s7 = 1.0000;

        if (p <= s0) {
          return u_color0;
        } else if (p <= s1) {
          return u_color0;
        } else if (p <= s2) {
          float f = smoothstep(s1, s2, p);
          return mix(u_color0, u_color1, f);
        } else if (p <= s3) {
          return u_color1;
        } else if (p <= s4) {
          float f = smoothstep(s3, s4, p);
          return mix(u_color1, u_color2, f);
        } else if (p <= s5) {
          return u_color2;
        } else if (p <= s6) {
          float f = smoothstep(s5, s6, p);
          return mix(u_color2, u_color3, f);
        } else {
          return u_color3;
        }
      }

      void main() {
        // Coordinates in pixels relative to viewport center
        vec2 pixelCoord = gl_FragCoord.xy;
        vec2 delta = (pixelCoord - u_center) / u_scale;

        // Angle in radians (CSS 0deg is to-top, 90deg is to-right; 32deg is rotated clockwise from vertical)
        float rad = u_angle * 0.017453292519943295;
        
        // Direction vectors
        // u is along-gradient, v is perpendicular cross-axis
        vec2 dirU = vec2(sin(rad), cos(rad));
        vec2 dirV = vec2(cos(rad), -sin(rad));

        float along = dot(delta, dirU) + 0.5;
        float crossAxis = dot(delta, dirV);

        // Cross-axis wave offset:
        float waveOffset = (u_wave / 100.0) * 0.35 * sin(crossAxis * 2.4 * 6.28318530718 + u_wave_clock);

        float p = along + waveOffset;

        vec3 color = sampleStripeField(p);

        // Film grain noise overlay (grain parameter = 42)
        if (u_grain > 0.0) {
          float n = pseudoNoise(gl_FragCoord.xy * 0.77 + vec2(fract(u_wave_clock * 0.05), fract(u_wave_clock * 0.03))) - 0.5;
          float grainFactor = (u_grain / 100.0) * 0.16;
          color += n * grainFactor;
        }

        gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
      }
    `;

    const createShader = (glCtx: WebGLRenderingContext, type: number, source: string) => {
      const shader = glCtx.createShader(type);
      if (!shader) return null;
      glCtx.shaderSource(shader, source);
      glCtx.compileShader(shader);
      if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
        console.error('Shader compile error:', glCtx.getShaderInfoLog(shader));
        glCtx.deleteShader(shader);
        return null;
      }
      return shader;
    };

    const vertexShader = createShader(gl, gl.VERTEX_SHADER, vsSource);
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
    if (!vertexShader || !fragmentShader) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program));
      return;
    }

    gl.useProgram(program);

    // Quad geometry
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    const vertices = new Float32Array([
      -1.0, -1.0,
       1.0, -1.0,
      -1.0,  1.0,
      -1.0,  1.0,
       1.0, -1.0,
       1.0,  1.0,
    ]);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

    const aPositionLoc = gl.getAttribLocation(program, 'a_position');
    gl.enableVertexAttribArray(aPositionLoc);
    gl.vertexAttribPointer(aPositionLoc, 2, gl.FLOAT, false, 0, 0);

    // Uniform locations
    const uResolutionLoc = gl.getUniformLocation(program, 'u_resolution');
    const uCenterLoc = gl.getUniformLocation(program, 'u_center');
    const uScaleLoc = gl.getUniformLocation(program, 'u_scale');
    const uAngleLoc = gl.getUniformLocation(program, 'u_angle');
    const uWaveLoc = gl.getUniformLocation(program, 'u_wave');
    const uWaveClockLoc = gl.getUniformLocation(program, 'u_wave_clock');
    const uGrainLoc = gl.getUniformLocation(program, 'u_grain');

    const uColor0Loc = gl.getUniformLocation(program, 'u_color0');
    const uColor1Loc = gl.getUniformLocation(program, 'u_color1');
    const uColor2Loc = gl.getUniformLocation(program, 'u_color2');
    const uColor3Loc = gl.getUniformLocation(program, 'u_color3');

    // Resize handler
    const updateSize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (width === 0 || height === 0) return;

      const displayWidth = Math.round(width * dpr);
      const displayHeight = Math.round(height * dpr);

      if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
        canvas.width = displayWidth;
        canvas.height = displayHeight;
        gl.viewport(0, 0, displayWidth, displayHeight);
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);

    // Render loop
    const render = (now: number) => {
      updateSize();

      const elapsedSeconds = (now - startTimeRef.current) / 1000.0;
      const speedFactor = config.speed / 100.0;
      const ph = elapsedSeconds * speedFactor;

      const amt = config.motionAmount;
      const dir = config.motionReverse ? -1.0 : 1.0;
      const spin = ph * dir;

      // Gentle natural swaying angle
      const animatedAngle = config.angle + Math.sin(spin * 0.6) * 28.0 * amt;

      // Natural wave clock advance
      const waveClock = 20.75 + ph * 1.2;

      gl.uniform2f(uResolutionLoc, canvas.width, canvas.height);

      const centerX = (config.centerX / 100.0) * canvas.width;
      const centerY = ((100.0 - config.centerY) / 100.0) * canvas.height;
      gl.uniform2f(uCenterLoc, centerX, centerY);

      const diag = Math.sqrt(canvas.width * canvas.width + canvas.height * canvas.height);
      const scalePixels = diag * (config.scale / 100.0);
      gl.uniform1f(uScaleLoc, scalePixels);

      // Steady wave vector: no velocity/vector increase!
      gl.uniform1f(uWaveLoc, config.wave);

      gl.uniform1f(uAngleLoc, animatedAngle);
      gl.uniform1f(uWaveClockLoc, waveClock);
      gl.uniform1f(uGrainLoc, config.grain);

      // Pass colors
      gl.uniform3f(uColor0Loc, rgbColors[0][0], rgbColors[0][1], rgbColors[0][2]);
      gl.uniform3f(uColor1Loc, rgbColors[1][0], rgbColors[1][1], rgbColors[1][2]);
      gl.uniform3f(uColor2Loc, rgbColors[2][0], rgbColors[2][1], rgbColors[2][2]);
      gl.uniform3f(uColor3Loc, rgbColors[3][0], rgbColors[3][1], rgbColors[3][2]);

      gl.drawArrays(gl.TRIANGLES, 0, 6);

      if (config.animated) {
        animationFrameRef.current = requestAnimationFrame(render);
      }
    };

    animationFrameRef.current = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', updateSize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [
    config.angle,
    config.scale,
    config.softness,
    config.wave,
    config.grain,
    config.animated,
    config.speed,
    config.motionAmount,
    config.motionReverse,
    config.centerX,
    config.centerY
  ]);

  return (
    <div className={`relative w-full h-full overflow-hidden ${className}`} style={style}>
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full block"
      />
      {children && (
        <div className="relative z-10 w-full h-full pointer-events-auto">
          {children}
        </div>
      )}
    </div>
  );
};
