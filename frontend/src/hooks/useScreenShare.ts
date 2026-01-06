export function useScreenShare() {
  const startScreenShare = async () => {
    return await navigator.mediaDevices.getDisplayMedia({
      video: true,
    });
  };

  return { startScreenShare };
}
