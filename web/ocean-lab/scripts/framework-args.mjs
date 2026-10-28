// Vite calls this flag --host; vinext calls it --hostname. Do not silently
// discard the caller's bind address when switching execution profiles.
export function normalizeDevArgs(args, managedLinux) {
  const result = [];
  const hostFlag = managedLinux ? "--host" : "--hostname";
  for (let index = 0; index < args.length; index++) {
    const arg = args[index];
    if (["--host", "--hostname", "-H"].includes(arg)) {
      const value = args[++index];
      if (!value || value.startsWith("-")) {
        throw new Error(`${arg} requires an explicit bind address (for example 127.0.0.1).`);
      }
      result.push(hostFlag, value);
    } else if (arg.startsWith("--host=") || arg.startsWith("--hostname=")) {
      const value = arg.slice(arg.indexOf("=") + 1);
      if (!value) throw new Error(`${arg} requires an explicit bind address.`);
      result.push(hostFlag, value);
    } else {
      result.push(arg);
    }
  }
  return result;
}
