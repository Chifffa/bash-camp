-- nvim-lspconfig: language servers, and the keymaps they bring. A server starts only where its
-- binary is found: mason brings lua_ls and basedpyright, bash-camp ruff; the rest are the host's.
return {
  "neovim/nvim-lspconfig",
  event = { "BufReadPre", "BufNewFile" },
  dependencies = {
    "hrsh7th/cmp-nvim-lsp",
    { "antosha417/nvim-lsp-file-operations", config = true },
    {
      "folke/lazydev.nvim",
      ft = "lua",
      opts = {
        -- luv's types, for code that uses vim.uv.
        library = { { path = "${3rd}/luv/library", words = { "vim%.uv" } } },
      },
    },
  },
  config = function()
    vim.api.nvim_create_autocmd("LspAttach", {
      group = vim.api.nvim_create_augroup("UserLspConfig", {}),
      callback = function(ev)
        local function map(mode, lhs, rhs, desc)
          vim.keymap.set(mode, lhs, rhs, { buffer = ev.buf, silent = false, desc = desc })
        end

        map("n", "<leader>cR", "<cmd>Telescope lsp_references<CR>", "Show LSP References")
        map("n", "<leader>cD", vim.lsp.buf.declaration, "Go to Declaration")
        map("n", "<leader>cd", "<cmd>Telescope lsp_definitions<CR>", "Go to Definition")
        map("n", "<leader>ci", "<cmd>Telescope lsp_implementations<CR>", "Show LSP Implementations")
        map("n", "<leader>ct", "<cmd>Telescope lsp_type_definitions<CR>", "Go to Type Definition")
        map({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, "Show Available Actions")
        map("n", "<leader>cr", vim.lsp.buf.rename, "Rename With LSP")
        map("n", "<leader>ch", vim.lsp.buf.hover, "Show Documentation Under Cursor")
        map("n", "<leader>dd", "<cmd>Telescope diagnostics bufnr=0<CR>", "Show Buffer Diagnostics")
        map("n", "<leader>dl", vim.diagnostic.open_float, "Show Line Diagnostics")
        map("n", "<leader>dk", function()
          vim.diagnostic.jump({ count = -1, float = true })
        end, "Go to Prev Diagnostic")
        map("n", "<leader>dj", function()
          vim.diagnostic.jump({ count = 1, float = true })
        end, "Go to Next Diagnostic")
      end,
    })

    local capabilities = require("cmp_nvim_lsp").default_capabilities()
    vim.lsp.config("*", { capabilities = capabilities })

    vim.lsp.config("lua_ls", {
      settings = {
        Lua = {
          diagnostics = { globals = { "vim" } },
          completion = { callSnippet = "Replace" },
          hint = { enable = true, setType = true, paramType = true },
        },
      },
    })
    vim.lsp.config("sourcekit", {
      capabilities = vim.tbl_deep_extend("keep", capabilities, {
        workspace = { didChangeWatchedFiles = { dynamicRegistration = true } },
      }),
    })
    vim.lsp.config("gopls", {
      settings = {
        gopls = {
          hints = {
            assignVariableTypes = true,
            compositeLiteralFields = true,
            compositeLiteralTypes = true,
            constantValues = true,
            functionTypeParameters = true,
            parameterNames = true,
            rangeVariableTypes = true,
          },
          analyses = {
            unreachable = true,
            unusedvariable = true,
            unusedparams = true,
            nilness = true,
          },
          staticcheck = true,
          gofumpt = true,
        },
      },
    })
    vim.lsp.config("basedpyright", {
      settings = {
        basedpyright = {
          analysis = {
            typeCheckingMode = "basic",
            reportAny = false,
            inlayHints = {
              variableTypes = true,
              pytestParameters = true,
              functionReturnTypes = true,
            },
          },
        },
      },
    })
    -- The nearest build marker is the root, else the repository. A root_dir function would have to
    -- take (bufnr, on_dir) since Neovim 0.11, so markers it is.
    vim.lsp.config("clangd", {
      filetypes = { "c", "cpp", "cuda" },
      root_markers = {
        {
          "Makefile",
          "configure.ac",
          "configure.in",
          "config.h.in",
          "meson.build",
          "meson_options.txt",
          "build.ninja",
          "CMakeLists.txt",
          "compile_commands.json",
          "compile_flags.txt",
          ".clangd",
        },
        ".git",
      },
    })
    vim.lsp.config("rust_analyzer", {
      settings = { ["rust-analyzer"] = { cargo = { allFeatures = true } } },
    })

    vim.lsp.enable({
      "basedpyright",
      "buf_ls",
      "clangd",
      "gopls",
      "lua_ls",
      "ruff",
      "rust_analyzer",
      "sourcekit",
      "yamlls",
    })

    vim.diagnostic.config({
      signs = {
        text = {
          [vim.diagnostic.severity.ERROR] = "",
          [vim.diagnostic.severity.WARN] = "",
          [vim.diagnostic.severity.INFO] = "",
          [vim.diagnostic.severity.HINT] = "󰠠",
        },
      },
    })
  end,
}
