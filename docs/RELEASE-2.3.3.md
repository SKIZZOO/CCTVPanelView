# CCTVPanelView 2.3.3 — Native ntfy video attachments

Replaces 2.3.2's quiet upload plus second Open video notification with one high-priority native MP4 attachment. This preserves the server's video MIME type, size and expiration so ntfy on iPhone can download and open the attachment with its native preview. No second external-link attachment, generic file row, or Preparing video preview message is generated.

On iPhone tap the MP4 to download, then tap again to play; use its menu to save/share. Check ntfy's Download attachments setting for automatic downloads, subject to client and iOS limitations. Server attachments normally expire after 3 hours. Previously expired attachments cannot be recovered from ntfy; full original recordings remain on the PC.

Compact H.264/AAC previews, bounded background encoding, local originals and outgoing category filters are preserved. No new cloud service or public camera endpoint is configured.

Previews now stay below 850 KB to cover 1 MB attachment download thresholds. Full-resolution recordings are unchanged. The synthetic native attachment was confirmed playable on the user's iPhone.

## Optional full recordings through Google Drive

Adds a selectable private Google Drive folder-link mode. A text-only ntfy notification identifies the recording filename/size and opens your configured private folder. It supports full local recordings such as 100 MB without reading/compressing/uploading those bytes to ntfy. Drive for desktop must sync the recording directory, and the phone must sign in with a permitted Google account. It does not confirm cloud upload or bypass Drive processing/storage limits. Folder sharing remains unchanged. Direct attachment mode remains available.
