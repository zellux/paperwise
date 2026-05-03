restartPendingBtn?.addEventListener("click", async () => {
  if (restartPendingBtn.disabled) {
    return;
  }
  const confirmed = window.confirm(
    "Restart analysis for all documents that are not ready?"
  );
  if (!confirmed) {
    return;
  }

  const response = await apiFetch("/documents/pending/restart?limit=200", {
    method: "POST",
  });
  const payload = await response.json();
  if (!response.ok) {
    logActivity(`Restart failed: ${payload.detail || response.statusText}`);
    return;
  }

  logActivity(
    `Restarted ${payload.restarted_count} pending document(s). ` +
      `${payload.skipped_ready_count} ready document(s) skipped.`
  );
  await loadPendingDocuments();
});
