-- nvim-surround: adds, changes and deletes surrounding pairs - ys, cs and ds.
return {
  "kylechui/nvim-surround",
  event = { "BufReadPre", "BufNewFile" },
  version = "*",
  config = true,
}
