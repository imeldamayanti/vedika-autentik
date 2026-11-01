// Worker entry: only the default handler may be exported from this module.
import { handle } from "./app.js";

export default {
  fetch: (request, env) => handle(request, env),
};
