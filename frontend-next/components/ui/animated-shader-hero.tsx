'use client';

import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

// Types for component props
interface HeroProps {
  trustBadge?: {
    text: string;
    icon?: React.ReactNode;
  };
  headline?: {
    line1: string;
    line2: string;
  };
  subtitle?: string;
  children?: React.ReactNode;
  className?: string;
}

// Sage/Cream themed shader - organic flowing forms inspired by nature
const sageShaderSource = `#version 300 es
/*
 * Sage & Cream Organic Shader
 * Inspired by flowing water, soft botanicals, and warm sunlight
 */
precision highp float;
out vec4 O;
uniform vec2 resolution;
uniform float time;
#define FC gl_FragCoord.xy
#define T time
#define R resolution
#define MN min(R.x,R.y)

// Pseudo random noise function
float rnd(vec2 p) {
  p = fract(p * vec2(12.9898, 78.233));
  p += dot(p, p + 34.56);
  return fract(p.x * p.y);
}

// Smooth value noise
float noise(in vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * (3. - 2. * f);
  float a = rnd(i),
        b = rnd(i + vec2(1, 0)),
        c = rnd(i + vec2(0, 1)),
        d = rnd(i + 1.);
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// Fractal brownian motion for organic textures
float fbm(vec2 p) {
  float t = 0., a = 1.;
  mat2 m = mat2(1., -0.5, 0.2, 1.2);
  for (int i = 0; i < 5; i++) {
    t += a * noise(p);
    p *= 2. * m;
    a *= 0.5;
  }
  return t;
}

// Soft organic cloud-like patterns
float organicFlow(vec2 p) {
  float d = 1., t = 0.;
  for (float i = 0.; i < 3.; i++) {
    float a = d * fbm(i * 8. + p.x * 0.15 + 0.18 * (1. + i) * p.y + d + i * i + p);
    t = mix(t, d, a);
    d = a;
    p *= 1.8 / (i + 1.);
  }
  return t;
}

void main(void) {
  vec2 uv = (FC - 0.5 * R) / MN;
  vec2 st = uv * vec2(2.2, 1.1);
  
  // Sage color palette for light particles only
  vec3 sageLight = vec3(0.847, 0.878, 0.847);    // #d8e0d8 - very light sage
  vec3 sageMid = vec3(0.627, 0.706, 0.627);      // #a0b4a0 - medium sage
  vec3 sageDark = vec3(0.376, 0.459, 0.376);     // #607560 - dark sage
  vec3 sageGlow = vec3(0.490, 0.560, 0.490);     // #7d8f7d - sage glow
  
  // Start with transparent background
  vec3 col = vec3(0.);
  float alpha = 0.;
  
  // Create flowing organic background for particle movement
  float bg = organicFlow(vec2(st.x + T * 0.12, -st.y * 0.8));
  
  // Gentle breathing effect
  uv *= 1. - 0.08 * (sin(T * 0.15) * 0.5 + 0.5);
  
  // Build up flowing light particles (enhanced visibility)
  for (float i = 1.; i < 8.; i++) {
    uv += 0.12 * cos(i * vec2(0.08 + 0.008 * i, 0.6) + i * i + T * 0.25 + 0.08 * uv.x);
    vec2 p = uv;
    float d = length(p);
    
    // Enhanced sage glow points (increased intensity)
    float glowIntensity = 0.003 / d;
    vec3 glowColor = mix(sageGlow, sageLight, 0.4);
    col += glowIntensity * glowColor;
    alpha += glowIntensity * 0.8;
    
    // Organic light streaks (enhanced)
    float b = noise(i + p + bg * 1.5);
    float streakIntensity = 0.004 * b / length(max(p, vec2(b * p.x * 0.015, p.y)));
    col += streakIntensity * mix(sageMid, sageDark, 0.3);
    alpha += streakIntensity * 0.6;
  }
  
  // Add flowing light texture
  float tex = fbm(uv * 3. + T * 0.05);
  col += tex * 0.02 * sageGlow;
  alpha += tex * 0.015;
  
  // Soft vignette for particles
  float vignette = 1. - length(uv) * 0.25;
  col *= vignette;
  alpha *= vignette;
  
  // Clamp alpha to reasonable range
  alpha = clamp(alpha, 0., 0.35);
  
  O = vec4(col, alpha);
}`;

// WebGL Renderer class
class WebGLRenderer {
  private canvas: HTMLCanvasElement;
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram | null = null;
  private vs: WebGLShader | null = null;
  private fs: WebGLShader | null = null;
  private buffer: WebGLBuffer | null = null;
  private scale: number;
  private shaderSource: string;
  private mouseMove = [0, 0];
  private mouseCoords = [0, 0];
  private pointerCoords = [0, 0];
  private nbrOfPointers = 0;

  private vertexSrc = `#version 300 es
precision highp float;
in vec4 position;
void main(){gl_Position=position;}`;

  private vertices = [-1, 1, -1, -1, 1, 1, 1, -1];

  constructor(canvas: HTMLCanvasElement, scale: number, shaderSource: string) {
    this.canvas = canvas;
    this.scale = scale;
    // Enable alpha channel for transparency
    this.gl = canvas.getContext('webgl2', { alpha: true, premultipliedAlpha: false })!;
    this.gl.viewport(0, 0, canvas.width * scale, canvas.height * scale);
    // Enable blending for transparency
    this.gl.enable(this.gl.BLEND);
    this.gl.blendFunc(this.gl.SRC_ALPHA, this.gl.ONE_MINUS_SRC_ALPHA);
    this.shaderSource = shaderSource;
  }

  updateShader(source: string) {
    this.reset();
    this.shaderSource = source;
    this.setup();
    this.init();
  }

  updateMove(deltas: number[]) {
    this.mouseMove = deltas;
  }

  updateMouse(coords: number[]) {
    this.mouseCoords = coords;
  }

  updatePointerCoords(coords: number[]) {
    this.pointerCoords = coords;
  }

  updatePointerCount(nbr: number) {
    this.nbrOfPointers = nbr;
  }

  updateScale(scale: number) {
    this.scale = scale;
    this.gl.viewport(0, 0, this.canvas.width * scale, this.canvas.height * scale);
  }

  compile(shader: WebGLShader, source: string) {
    const gl = this.gl;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(shader);
      console.error('Shader compilation error:', error);
    }
  }

  test(source: string) {
    let result = null;
    const gl = this.gl;
    const shader = gl.createShader(gl.FRAGMENT_SHADER)!;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      result = gl.getShaderInfoLog(shader);
    }
    gl.deleteShader(shader);
    return result;
  }

  reset() {
    const gl = this.gl;
    if (this.program && !gl.getProgramParameter(this.program, gl.DELETE_STATUS)) {
      if (this.vs) {
        gl.detachShader(this.program, this.vs);
        gl.deleteShader(this.vs);
      }
      if (this.fs) {
        gl.detachShader(this.program, this.fs);
        gl.deleteShader(this.fs);
      }
      gl.deleteProgram(this.program);
    }
  }

  setup() {
    const gl = this.gl;
    this.vs = gl.createShader(gl.VERTEX_SHADER)!;
    this.fs = gl.createShader(gl.FRAGMENT_SHADER)!;
    this.compile(this.vs, this.vertexSrc);
    this.compile(this.fs, this.shaderSource);
    this.program = gl.createProgram()!;
    gl.attachShader(this.program, this.vs);
    gl.attachShader(this.program, this.fs);
    gl.linkProgram(this.program);

    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(this.program));
    }
  }

  init() {
    const gl = this.gl;
    const program = this.program!;
    
    this.buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(this.vertices), gl.STATIC_DRAW);

    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    (program as any).resolution = gl.getUniformLocation(program, 'resolution');
    (program as any).time = gl.getUniformLocation(program, 'time');
    (program as any).move = gl.getUniformLocation(program, 'move');
    (program as any).touch = gl.getUniformLocation(program, 'touch');
    (program as any).pointerCount = gl.getUniformLocation(program, 'pointerCount');
    (program as any).pointers = gl.getUniformLocation(program, 'pointers');
  }

  render(now = 0) {
    const gl = this.gl;
    const program = this.program;
    
    if (!program || gl.getProgramParameter(program, gl.DELETE_STATUS)) return;

    gl.clearColor(0, 0, 0, 0); // Transparent background
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    
    gl.uniform2f((program as any).resolution, this.canvas.width, this.canvas.height);
    gl.uniform1f((program as any).time, now * 1e-3);
    gl.uniform2f((program as any).move, ...this.mouseMove);
    gl.uniform2f((program as any).touch, ...this.mouseCoords);
    gl.uniform1i((program as any).pointerCount, this.nbrOfPointers);
    gl.uniform2fv((program as any).pointers, this.pointerCoords);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
}

// Pointer Handler class
class PointerHandler {
  private scale: number;
  private active = false;
  private pointers = new Map<number, number[]>();
  private lastCoords = [0, 0];
  private moves = [0, 0];

  constructor(element: HTMLCanvasElement, scale: number) {
    this.scale = scale;
    
    const map = (element: HTMLCanvasElement, scale: number, x: number, y: number) => 
      [x * scale, element.height - y * scale];

    element.addEventListener('pointerdown', (e) => {
      this.active = true;
      this.pointers.set(e.pointerId, map(element, this.getScale(), e.clientX, e.clientY));
    });

    element.addEventListener('pointerup', (e) => {
      if (this.count === 1) {
        this.lastCoords = this.first;
      }
      this.pointers.delete(e.pointerId);
      this.active = this.pointers.size > 0;
    });

    element.addEventListener('pointerleave', (e) => {
      if (this.count === 1) {
        this.lastCoords = this.first;
      }
      this.pointers.delete(e.pointerId);
      this.active = this.pointers.size > 0;
    });

    element.addEventListener('pointermove', (e) => {
      if (!this.active) return;
      this.lastCoords = [e.clientX, e.clientY];
      this.pointers.set(e.pointerId, map(element, this.getScale(), e.clientX, e.clientY));
      this.moves = [this.moves[0] + e.movementX, this.moves[1] + e.movementY];
    });
  }

  getScale() {
    return this.scale;
  }

  updateScale(scale: number) {
    this.scale = scale;
  }

  get count() {
    return this.pointers.size;
  }

  get move() {
    return this.moves;
  }

  get coords() {
    return this.pointers.size > 0 
      ? Array.from(this.pointers.values()).flat() 
      : [0, 0];
  }

  get first() {
    return this.pointers.values().next().value || this.lastCoords;
  }
}

// Custom hook for shader background
const useShaderBackground = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const rendererRef = useRef<WebGLRenderer | null>(null);
  const pointersRef = useRef<PointerHandler | null>(null);

  const resize = () => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const dpr = Math.max(1, 0.5 * window.devicePixelRatio);
    
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    
    if (rendererRef.current) {
      rendererRef.current.updateScale(dpr);
    }
  };

  const loop = (now: number) => {
    if (!rendererRef.current || !pointersRef.current) return;
    
    rendererRef.current.updateMouse(pointersRef.current.first);
    rendererRef.current.updatePointerCount(pointersRef.current.count);
    rendererRef.current.updatePointerCoords(pointersRef.current.coords);
    rendererRef.current.updateMove(pointersRef.current.move);
    rendererRef.current.render(now);
    animationFrameRef.current = requestAnimationFrame(loop);
  };

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const dpr = Math.max(1, 0.5 * window.devicePixelRatio);
    
    rendererRef.current = new WebGLRenderer(canvas, dpr, sageShaderSource);
    pointersRef.current = new PointerHandler(canvas, dpr);
    
    rendererRef.current.setup();
    rendererRef.current.init();
    
    resize();
    
    if (rendererRef.current.test(sageShaderSource) === null) {
      rendererRef.current.updateShader(sageShaderSource);
    }
    
    loop(0);
    
    window.addEventListener('resize', resize);
    
    return () => {
      window.removeEventListener('resize', resize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (rendererRef.current) {
        rendererRef.current.reset();
      }
    };
  }, []);

  return canvasRef;
};

// Animation variants for framer-motion
const fadeInDown = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0 }
};

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0 }
};

// Animated Shader Hero Component
const AnimatedShaderHero: React.FC<HeroProps> = ({
  trustBadge,
  headline,
  subtitle,
  children,
  className = ""
}) => {
  const canvasRef = useShaderBackground();

  return (
    <div className={`relative w-full ${className || 'min-h-screen'} overflow-hidden`}>
      {/* Shader Canvas Background - Transparent with flowing lights */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full object-cover touch-none"
        style={{ background: 'transparent' }}
      />
      
      {/* Hero Content Overlay */}
      {children ? (
        // Custom content mode - just render children
        children
      ) : (
        // Default content mode - render headline and subtitle
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pt-16 pb-8 px-6">
          {/* Trust Badge */}
          {trustBadge && (
            <motion.div 
              className="mb-8"
              initial="hidden"
              animate="visible"
              variants={fadeInDown}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <div className="flex items-center gap-2 px-5 py-2.5 bg-sage-100/60 backdrop-blur-md border border-sage-300/40 rounded-full text-sm shadow-sm">
                {trustBadge.icon && (
                  <span className="text-sage-600">
                    {trustBadge.icon}
                  </span>
                )}
                <span className="text-sage-700 font-medium">{trustBadge.text}</span>
              </div>
            </motion.div>
          )}

          <div className="text-center space-y-6 max-w-5xl mx-auto">
            {/* Main Heading with Editorial Typography */}
            {headline && (
              <div className="space-y-3">
                <motion.h1 
                  className="text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-serif font-bold tracking-tight bg-gradient-to-r from-sage-800 via-sage-600 to-sage-700 bg-clip-text text-transparent"
                  initial="hidden"
                  animate="visible"
                  variants={fadeInUp}
                  transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                  aria-label={headline.line1}
                >
                  {headline.line1}
                </motion.h1>
                <motion.h2 
                  className="text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-serif font-bold tracking-tight bg-gradient-to-r from-sage-600 via-sage-500 to-sage-400 bg-clip-text text-transparent"
                  initial="hidden"
                  animate="visible"
                  variants={fadeInUp}
                  transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
                  aria-label={headline.line2}
                >
                  {headline.line2}
                </motion.h2>
              </div>
            )}
            
            {/* Subtitle with Animation */}
            {subtitle && (
              <motion.div 
                className="max-w-3xl mx-auto"
                initial="hidden"
                animate="visible"
                variants={fadeInUp}
                transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
              >
                <p className="text-lg md:text-xl lg:text-2xl text-charcoal-light/90 font-light leading-relaxed">
                  {subtitle}
                </p>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnimatedShaderHero;
