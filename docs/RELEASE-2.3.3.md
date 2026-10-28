# CCTVPanelView 2.3.3 — Native ntfy video attachments

Replaces 2.3.2's quiet upload plus second Open video notification with one high-priority native MP4 attachment. This preserves the server's video MIME type, size and expiration so ntfy on iPhone can download and open the attachment with its native preview. No second external-link attachment, generic file row, or Preparing video preview message is generated.

On iPhone tap the MP4 to download, then tap again to play; use its menu to save/share. Check ntfy's Download attachments setting for automatic downloads, subject to client and iOS limitations. Server attachments normally expire after 3 hours. Previously expired attachments cannot be recovered from ntfy; full original recordings remain on the PC.

Compact H.264/AAC previews, bounded background encoding, local originals and outgoing category filters are preserved. No new cloud service or public camera endpoint is configured.

Previews now stay below 850 KB to cover 1 MB attachment download thresholds. Full-resolution recordings are unchanged. The synthetic native attachment was confirmed playable on the user's iPhone.

## Full recordings through a folder picker

Select a synced folder on Google Drive for desktop's virtual drive. Its private browser link is resolved automatically from local Drive metadata. Completed recordings already inside it stay in place; others are copied there in bounded chunks without overwriting originals. A small ntfy notification identifies the file/size and opens the private folder. This supports files such as 100 MB without uploading those bytes to ntfy or requiring API setup/pasted links.

Google Drive must finish syncing and processing before playback. The notification does not confirm cloud upload. Sharing is unchanged. Non-Drive folders, unavailable drives, temporary local folder IDs and unsupported metadata produce a clear error instead of a guessed link. Local metadata resolution was verified against the existing Drive for desktop recordings folder on the user's PC. Native attachment playback was confirmed on iPhone using one authorized synthetic video.
