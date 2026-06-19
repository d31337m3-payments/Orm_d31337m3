import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export default function Drawer({ open, onClose, title, children, testid }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose} data-testid={`${testid}-overlay`}
          className="fixed inset-0 z-[90] bg-black/70 backdrop-blur-sm"
        >
          <motion.div
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "tween", duration: 0.25, ease: "easeOut" }}
            onClick={(e) => e.stopPropagation()}
            data-testid={testid}
            className="absolute top-0 right-0 h-full w-full max-w-2xl bg-[#0a0a0a] border-l border-[#222] overflow-y-auto"
          >
            <div className="sticky top-0 z-10 border-b border-[#222] bg-[#0a0a0a]/95 backdrop-blur px-6 py-4 flex justify-between items-center">
              <div>
                <div className="overline mb-1">// detail</div>
                <h3 className="font-display font-bold text-xl">{title}</h3>
              </div>
              <button onClick={onClose} data-testid={`${testid}-close`} className="text-zinc-400 hover:text-[#FF3333]">
                <X size={20}/>
              </button>
            </div>
            <div className="p-6">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export const Field = ({ label, value, mono = true }) => (
  <div className="border-b border-[#222] py-2">
    <div className="overline mb-1">{label}</div>
    <div className={`${mono ? "font-mono" : "font-display"} text-sm text-white break-all`}>{value ?? "—"}</div>
  </div>
);
