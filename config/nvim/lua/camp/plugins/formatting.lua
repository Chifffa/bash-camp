-- conform: formats on save, with the tools bash-camp's `check` holds the code to.
return {
  "stevearc/conform.nvim",
  event = { "BufReadPre", "BufNewFile" },
  config = function()
    local conform = require("conform")
    local format = { lsp_format = "fallback", async = false, timeout_ms = 1000 }

    conform.setup({
      formatters_by_ft = {
        lua = { "stylua" },
        python = { "ruff_format" },
        sh = { "shfmt" },
        toml = { "tombi" },
        tex = { "tex-fmt" },
      },
      formatters = {
        -- bash-camp's shell style; shfmt alone indents with tabs.
        shfmt = { prepend_args = { "-i", "2", "-ci" } },
      },
      format_on_save = format,
    })

    vim.keymap.set({ "n", "v" }, "<leader>cf", function()
      conform.format(format)
    end, { desc = "Format" })
  end,
}
