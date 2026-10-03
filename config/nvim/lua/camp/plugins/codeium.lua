-- Codeium: AI completions as virtual text. Tab accepts one, Alt-] and Alt-[ cycle through them.
-- `:Codeium Auth` signs in, once per machine.
return {
  "Exafunction/codeium.nvim",
  event = "InsertEnter",
  dependencies = { "nvim-lua/plenary.nvim", "hrsh7th/nvim-cmp" },
  opts = {
    virtual_text = { enabled = true },
  },
}
