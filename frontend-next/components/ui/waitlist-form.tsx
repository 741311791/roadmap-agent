"use client";

import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";
import { ArrowRight, Sparkles } from "lucide-react";

const SMALL_BREAKPOINT = 570;

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.2 } },
};

const childVariants = {
  hidden: { opacity: 0, filter: "blur(10px)" },
  visible: {
    opacity: 1,
    filter: "blur(0px)",
    transition: { duration: 0.5 },
  },
};

// Hook to track window width
function useWindowWidth() {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    setWidth(window.innerWidth);
    const handleResize = () => setWidth(window.innerWidth);

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return width;
}

interface WaitlistFormProps {
  onSubmit?: (email: string) => Promise<void> | void;
  isSubmitting?: boolean;
  showTitle?: boolean;
  className?: string;
}

const WaitlistForm: React.FC<WaitlistFormProps> = ({ 
  onSubmit, 
  isSubmitting = false,
  showTitle = false,
  className = ""
}) => {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [localSubmitting, setLocalSubmitting] = useState(false);
  const width = useWindowWidth();

  const triggerSageConfetti = () => {
    // Sage-themed confetti
    const colors = ['#607560', '#7d8f7d', '#a3b1a3', '#c7d0c7'];
    
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: colors,
      ticks: 200,
    });
  };

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !email.includes('@')) return;
    
    setLocalSubmitting(true);
    
    try {
      if (onSubmit) {
        await onSubmit(email);
      }
      setSubmitted(true);
      triggerSageConfetti();
      setEmail('');
    } catch (error) {
      console.error('Failed to submit:', error);
    } finally {
      setLocalSubmitting(false);
    }
  }, [email, onSubmit]);

  const isLoading = isSubmitting || localSubmitting;

  const ThankYouMessage = (
    <motion.div
      layout
      initial={{ opacity: 0, filter: "blur(10px)" }}
      animate={{
        opacity: 1,
        filter: "blur(0px)",
        transition: { duration: 0.5 },
      }}
      exit={{
        opacity: 0,
        filter: "blur(10px)",
        transition: { duration: 0.5 },
      }}
    >
      <div className="flex flex-col items-center justify-center text-center space-y-4">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="w-16 h-16 bg-sage-100 rounded-full flex items-center justify-center"
        >
          <Sparkles className="w-8 h-8 text-sage-600" />
        </motion.div>
        <h2 className="text-3xl md:text-4xl font-serif font-bold bg-gradient-to-b from-sage-600 to-sage-800 bg-clip-text text-transparent">
          You're on the List!
        </h2>
        <p className="text-base md:text-lg text-charcoal-light/80">
          We'll notify you as soon as access becomes available.
        </p>
      </div>
    </motion.div>
  );

  const FormContent = (
    <motion.div
      layout
      key="form"
      className="w-full"
      initial={{ opacity: 0, filter: "blur(10px)" }}
      animate={{
        opacity: 1,
        filter: "blur(0px)",
        transition: { duration: 0.5 },
      }}
      exit={{
        opacity: 0,
        filter: "blur(10px)",
        transition: { duration: 0.5 },
      }}
    >
      {showTitle && (
        <motion.div
          className={`${
            width <= SMALL_BREAKPOINT ? "text-left mb-6" : "text-center mb-8"
          }`}
          variants={childVariants}
        >
          <h2 className="text-3xl md:text-4xl font-serif font-bold bg-gradient-to-b from-sage-700 to-sage-900 bg-clip-text text-transparent">
            Join the Waitlist for
            <span
              className={`pl-2 ${
                width <= SMALL_BREAKPOINT ? "" : "block"
              } bg-gradient-to-r from-sage-500 to-sage-700 bg-clip-text text-transparent`}
            >
              Fast Learning
            </span>
          </h2>
        </motion.div>
      )}

      <motion.form
        onSubmit={handleSubmit}
        className={
          width <= SMALL_BREAKPOINT
            ? "flex flex-col gap-3 items-start w-full"
            : "relative w-full"
        }
        style={
          width > SMALL_BREAKPOINT
            ? { maxWidth: '600px', margin: '0 auto', textAlign: 'center', verticalAlign: 'middle' }
            : undefined
        }
        variants={childVariants}
      >
        <div
          className={
            width <= SMALL_BREAKPOINT
              ? "flex flex-col gap-3 w-full"
              : "flex flex-row items-center w-full space-x-3 rounded-full border-2 border-sage-200/50 bg-white/95 backdrop-blur-md p-0.5 shadow-lg hover:border-sage-300/60 transition-all"
          }
          style={
            width > SMALL_BREAKPOINT
              ? { textAlign: 'center', verticalAlign: 'middle' }
              : undefined
          }
        >
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            className={`${
              width <= SMALL_BREAKPOINT
                ? "px-5 py-4 w-full text-base focus:outline-none rounded-full border-2 border-sage-200/50 bg-white/95 backdrop-blur-md shadow-md focus:border-sage-400 focus:ring-2 focus:ring-sage-400/20 transition-all"
                : "flex-1 rounded-full bg-transparent px-5 text-base focus:outline-none placeholder:text-muted-foreground"
            }`}
            style={
              width > SMALL_BREAKPOINT
                ? { height: '46px' }
                : undefined
            }
            required
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className={`${
              width <= SMALL_BREAKPOINT
                ? "rounded-full bg-gradient-to-r from-sage-600 to-sage-700 px-6 py-4 text-base font-semibold text-white hover:from-sage-700 hover:to-sage-800 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed w-full flex items-center justify-center gap-2"
                : "rounded-full bg-gradient-to-r from-sage-600 to-sage-700 px-8 text-base font-semibold text-white hover:from-sage-700 hover:to-sage-800 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
            }`}
            style={
              width > SMALL_BREAKPOINT
                ? { height: '46px', justifyContent: 'flex-start', gap: '18px' }
                : undefined
            }
          >
            {isLoading ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                />
                Joining...
              </>
            ) : (
              <>
                Join Waitlist
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </motion.form>

      <motion.p 
        className="mt-4 text-xs md:text-sm text-muted-foreground/80 text-center"
        variants={childVariants}
      >
        Be the first to experience the future of learning. No spam, ever.
      </motion.p>
    </motion.div>
  );

  return (
    <motion.div
      layout
      className={`w-full max-w-2xl ${className}`}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <AnimatePresence mode="wait">
        {!submitted ? FormContent : ThankYouMessage}
      </AnimatePresence>
    </motion.div>
  );
};

export { WaitlistForm };

