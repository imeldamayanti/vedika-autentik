export const fail = (status, kode, pesan) => Object.assign(new Error(pesan), { status, kode });

export const json = (body, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });

export const galat = (error) => json({ galat: { kode: error.kode, pesan: error.message } }, error.status);

// Python's max_length counts code points; String.length counts UTF-16 units.
export const length = (value) => [...value].length;

export const isText = (value, min, max) =>
  typeof value === "string" && length(value) >= min && length(value) <= max;
