-- noice: the command line in a popup. Its messages, notifications and LSP progress stay off.
return {
  "folke/noice.nvim",
  event = "VeryLazy",
  dependencies = { "MunifTanjim/nui.nvim" },
  opts = {
    lsp = {
      -- Hover and completion docs, rendered by treesitter.
      override = {
        ["vim.lsp.util.convert_input_to_markdown_lines"] = true,
        ["vim.lsp.util.stylize_markdown"] = true,
        ["cmp.entry.get_documentation"] = true,
      },
      progress = { enabled = false },
      signature = { enabled = false },
    },
    presets = {
      bottom_search = false,
      long_message_to_split = true,
      inc_rename = false,
      lsp_doc_border = false,
    },
    messages = { enabled = false },
    cmdline = { enabled = true },
    notify = { enabled = false },
  },
}
