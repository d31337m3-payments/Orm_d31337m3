import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export default function FeatureDialog({ open, onClose, feature }) {
  return (
    <AnimatePresence>
      {open && feature && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm"
          onClick={onClose}
          data-testid="feature-dialog-overlay"
        >
          <motion.div
            initial={{ y: 30, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 30, opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            className="brutal-card max-w-2xl w-full p-8 relative bg-[#0a0a0a] border-[#FF3333]"
            data-testid="feature-dialog"
          >
            <button onClick={onClose} data-testid="feature-dialog-close" className="absolute top-4 right-4 text-zinc-500 hover:text-[#FF3333]">
              <X size={20} />
            </button>
            <div className="flex items-center gap-3 mb-1">
              {feature.icon && <feature.icon className="text-[#FF3333]" size={28} />}
              <div className="overline">// {feature.tag}</div>
            </div>
            <h2 className="font-display font-black text-3xl mb-4 leading-tight">{feature.title}</h2>
            <p className="font-mono text-sm text-zinc-300 leading-relaxed mb-4">{feature.body}</p>
            <div className="border-l-2 border-[#FF3333] pl-4 mb-4">
              <div className="overline mb-2">// how it works</div>
              <ul className="space-y-2">
                {feature.howItWorks?.map((step, i) => (
                  <li key={i} className="font-mono text-sm text-zinc-400 flex gap-3">
                    <span className="text-[#FF3333] font-bold">{String(i + 1).padStart(2, "0")}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
            {feature.stat && (
              <div className="border border-[#222] p-4 bg-black flex items-center justify-between">
                <div className="overline">{feature.stat.label}</div>
                <div className="font-display font-black text-3xl text-[#00FF41]">{feature.stat.value}</div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
