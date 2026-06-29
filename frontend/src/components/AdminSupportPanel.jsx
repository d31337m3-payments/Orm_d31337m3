import React, { useCallback, useEffect, useMemo, useState } from "react";
import adminApi from "@/lib/adminApi";

export default function AdminSupportPanel() {
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [chats, setChats] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [replyText, setReplyText] = useState("");
  const [ticketSubject, setTicketSubject] = useState("Support request from live chat");
  const [ticketDesc, setTicketDesc] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setNotice("");
    try {
      const [c, t] = await Promise.all([adminApi.supportAdminChats(), adminApi.supportAdminTickets()]);
      setChats(c || []);
      setTickets(t || []);
      if (selectedChat?.id) {
        const r = await adminApi.supportAdminChatMessages(selectedChat.id);
        setSelectedChat(r.chat || selectedChat);
        setMessages(r.messages || []);
      }
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to load support data.");
    } finally {
      setLoading(false);
    }
  }, [selectedChat]);

  useEffect(() => { refresh(); }, [refresh]);

  const openChat = async (chat) => {
    try {
      const r = await adminApi.supportAdminChatMessages(chat.id);
      setSelectedChat(r.chat || chat);
      setMessages(r.messages || []);
      setNotice("");
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to open chat.");
    }
  };

  const sendReply = async () => {
    if (!selectedChat?.id || !replyText.trim()) return;
    try {
      await adminApi.supportAdminSendMessage(selectedChat.id, replyText.trim());
      setReplyText("");
      await openChat(selectedChat);
      await refresh();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to send reply.");
    }
  };

  const createTicketFromChat = async () => {
    if (!selectedChat?.id) return;
    try {
      const r = await adminApi.supportAdminCreateTicketFromChat(selectedChat.id, {
        subject: ticketSubject,
        description: ticketDesc,
        priority: "normal",
      });
      if (!r?.ok) {
        setNotice(r?.message || "Failed to create linked ticket.");
        return;
      }
      setTicketDesc("");
      setNotice("Ticket created and linked to selected customer chat.");
      await refresh();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to create linked ticket.");
    }
  };

  const patchTicket = async (ticketId, status) => {
    try {
      const r = await adminApi.supportAdminPatchTicket(ticketId, { status });
      if (!r?.ok) {
        setNotice(r?.message || "Failed to update ticket.");
        return;
      }
      await refresh();
    } catch (e) {
      setNotice(e?.response?.data?.detail || "Failed to update ticket.");
    }
  };

  const linkedTickets = useMemo(
    () => (selectedChat ? tickets.filter((t) => t.chat_id === selectedChat.id) : []),
    [tickets, selectedChat]
  );

  if (loading) return <div className="font-mono text-zinc-500">loading support<span className="blink">_</span></div>;

  return (
    <div className="space-y-6" data-testid="admin-support-panel">
      {notice && <div className="brutal-card p-3 font-mono text-xs text-zinc-300">{notice}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="brutal-card p-4 lg:col-span-1">
          <div className="overline mb-3">// live chats</div>
          <div className="space-y-2 max-h-[520px] overflow-y-auto">
            {chats.length === 0 && <div className="font-mono text-xs text-zinc-500">No active customer chats.</div>}
            {chats.map((c) => (
              <button
                key={c.id}
                className={`w-full text-left border p-3 font-mono text-xs ${selectedChat?.id === c.id ? "border-white" : "border-[#222]"}`}
                onClick={() => openChat(c)}
              >
                <div className="text-white">{c.customer_email || c.customer_id}</div>
                <div className="text-zinc-500">{c.status} · msgs {c.messages_count || 0} · tickets {c.tickets_count || 0}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="brutal-card p-4 lg:col-span-2">
          <div className="overline mb-3">// chat thread</div>
          {!selectedChat ? (
            <div className="font-mono text-xs text-zinc-500">Select a chat to view and reply.</div>
          ) : (
            <>
              <div className="font-mono text-xs text-zinc-400 mb-2">Customer: <span className="text-white">{selectedChat.customer_email || selectedChat.customer_id}</span></div>
              <div className="border border-[#222] p-3 h-[260px] overflow-y-auto mb-3 bg-black/40">
                {messages.length === 0 && <div className="font-mono text-xs text-zinc-500">No messages yet.</div>}
                {messages.map((m) => (
                  <div key={m.id} className="mb-2">
                    <div className="font-mono text-[10px] text-zinc-500">{m.sender_role?.toUpperCase()} · {String(m.sent_at || "").slice(0, 19)}</div>
                    <div className="font-mono text-xs text-zinc-200 whitespace-pre-wrap">{m.text}</div>
                  </div>
                ))}
              </div>

              <div className="flex gap-2 mb-4">
                <input
                  className="brutal-input flex-1"
                  placeholder="Reply to customer"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendReply()}
                />
                <button className="brutal-btn" onClick={sendReply}>Send</button>
              </div>

              <div className="border-t border-[#222] pt-4">
                <div className="overline mb-2">// create linked ticket</div>
                <input className="brutal-input mb-2" value={ticketSubject} onChange={(e) => setTicketSubject(e.target.value)} placeholder="Ticket subject" />
                <textarea className="brutal-input min-h-[80px]" value={ticketDesc} onChange={(e) => setTicketDesc(e.target.value)} placeholder="Ticket details" />
                <button className="brutal-btn mt-2" onClick={createTicketFromChat}>Create Ticket From This Chat</button>
              </div>

              <div className="border-t border-[#222] pt-4 mt-4">
                <div className="overline mb-2">// linked tickets</div>
                {linkedTickets.length === 0 && <div className="font-mono text-xs text-zinc-500">No linked tickets yet.</div>}
                {linkedTickets.map((t) => (
                  <div key={t.id} className="border border-[#222] p-2 mb-2 font-mono text-xs">
                    <div className="text-white">{t.subject}</div>
                    <div className="text-zinc-500">{t.status} · {t.priority}</div>
                    <div className="mt-2 flex gap-2">
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => patchTicket(t.id, "open")}>open</button>
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => patchTicket(t.id, "in_progress")}>in progress</button>
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => patchTicket(t.id, "resolved")}>resolved</button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="brutal-card p-4">
        <div className="overline mb-3">// all tickets</div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#222]">
                <th className="text-left overline py-2">customer</th>
                <th className="text-left overline py-2">subject</th>
                <th className="text-left overline py-2">chat</th>
                <th className="text-left overline py-2">status</th>
              </tr>
            </thead>
            <tbody>
              {tickets.length === 0 && (
                <tr><td colSpan={4} className="py-3 font-mono text-xs text-zinc-500">No tickets.</td></tr>
              )}
              {tickets.map((t) => (
                <tr key={t.id} className="border-b border-[#222]">
                  <td className="py-2 font-mono text-xs">{t.customer_email || t.customer_id}</td>
                  <td className="py-2 font-mono text-xs text-zinc-300">{t.subject}</td>
                  <td className="py-2 font-mono text-xs text-zinc-500">{t.chat_id ? t.chat_id.slice(0, 8) : "—"}</td>
                  <td className="py-2 font-mono text-xs text-zinc-400">{t.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
