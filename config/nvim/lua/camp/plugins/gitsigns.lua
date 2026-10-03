-- gitsigns: changes in the sign column, and hunks staged, reset, previewed and blamed in place.
return {
  "lewis6991/gitsigns.nvim",
  event = { "BufReadPre", "BufNewFile" },
  opts = {
    on_attach = function(bufnr)
      local gs = package.loaded.gitsigns

      local function map(mode, lhs, rhs, desc)
        vim.keymap.set(mode, lhs, rhs, { buffer = bufnr, desc = desc })
      end
      local function selection()
        return { vim.fn.line("."), vim.fn.line("v") }
      end

      map("n", "<leader>gj", function()
        gs.nav_hunk("next")
      end, "Next Hunk")
      map("n", "<leader>gk", function()
        gs.nav_hunk("prev")
      end, "Prev Hunk")

      map("n", "<leader>gs", gs.stage_hunk, "Stage Hunk")
      map("v", "<leader>gs", function()
        gs.stage_hunk(selection())
      end, "Stage Hunk")
      map("n", "<leader>gr", gs.reset_hunk, "Reset Hunk")
      map("v", "<leader>gr", function()
        gs.reset_hunk(selection())
      end, "Reset Hunk")
      map("n", "<leader>gS", gs.stage_buffer, "Stage Buffer")
      map("n", "<leader>gR", gs.reset_buffer, "Reset Buffer")
      -- Staging a staged hunk unstages it.
      map("n", "<leader>gu", gs.stage_hunk, "Unstage Hunk")
      map("n", "<leader>gp", gs.preview_hunk, "Preview Hunk")

      map("n", "<leader>gb", function()
        gs.blame_line({ full = true })
      end, "Blame Line")
      map("n", "<leader>gB", gs.toggle_current_line_blame, "Toggle Line Blame")
      map("n", "<leader>gd", gs.diffthis, "Diff This")
      map("n", "<leader>gD", function()
        gs.diffthis("~")
      end, "Diff This ~")
    end,
  },
}
