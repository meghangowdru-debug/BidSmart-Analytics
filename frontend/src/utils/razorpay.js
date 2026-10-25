const CHECKOUT_SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';

export const loadRazorpayCheckout = () => {
  if (window.Razorpay) return Promise.resolve(window.Razorpay);

  return new Promise((resolve, reject) => {
    const existingScript = document.querySelector(
      `script[src="${CHECKOUT_SCRIPT_URL}"]`,
    );
    const script = existingScript || document.createElement('script');
    const cleanup = () => {
      script.removeEventListener('load', onLoad);
      script.removeEventListener('error', onError);
    };
    const onLoad = () => {
      cleanup();
      if (window.Razorpay) resolve(window.Razorpay);
      else reject(new Error('Razorpay Checkout did not initialize.'));
    };
    const onError = () => {
      cleanup();
      reject(new Error('Unable to load Razorpay Checkout. Check your connection and retry.'));
    };

    script.addEventListener('load', onLoad, { once: true });
    script.addEventListener('error', onError, { once: true });
    if (!existingScript) {
      script.src = CHECKOUT_SCRIPT_URL;
      script.async = true;
      document.body.appendChild(script);
    }
  });
};
