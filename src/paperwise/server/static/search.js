searchKeywordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runKeywordSearch();
});

searchAskForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runAsk();
});

searchAskNewChatBtn?.addEventListener("click", () => {
  resetSearchAskChat();
  logActivity("Ask Your Docs chat reset.");
});

searchAskThreadSearch?.addEventListener("input", () => {
  loadSearchAskThreads().catch((error) => {
    logActivity(`Chat history failed: ${error.message}`);
  });
});

searchAskThreadList?.addEventListener("click", async (event) => {
  const deleteButton = event.target instanceof Element ? event.target.closest("[data-delete-thread-id]") : null;
  if (deleteButton instanceof HTMLElement) {
    await deleteSearchAskThread(deleteButton.dataset.deleteThreadId || "");
    return;
  }
  const threadButton = event.target instanceof Element ? event.target.closest("[data-thread-id]") : null;
  if (threadButton instanceof HTMLElement) {
    await loadSearchAskThread(threadButton.dataset.threadId || "");
  }
});

searchAskQuestion?.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.metaKey || event.ctrlKey || event.altKey) {
    return;
  }
  event.preventDefault();
  await runAsk();
});

function autoResizeChatTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

if (searchAskQuestion) {
  searchAskQuestion.addEventListener("input", () => autoResizeChatTextarea(searchAskQuestion));
}

searchAskMessages?.addEventListener("click", (event) => {
  const button = event.target instanceof Element ? event.target.closest(".chat-status-summary") : null;
  if (!(button instanceof HTMLElement)) {
    return;
  }
  const message = searchAskMessagesState.find((item) => item.id === button.dataset.messageId);
  if (!message) {
    return;
  }
  if (message.activity) {
    const roundIndex = Number(button.dataset.roundIndex || 0);
    const round = message.activityRounds.find((item) => Number(item.index) === roundIndex);
    if (!round || !round.details?.length) {
      return;
    }
    round.expanded = !round.expanded;
    renderSearchAskMessages();
    return;
  }
  if (!message.statusDetail) {
    return;
  }
  message.expanded = !message.expanded;
  renderSearchAskMessages();
});
