export const silentReloading = { value: false };

export function reloadSilently(): void {
  silentReloading.value = true;
  window.location.reload();
}
