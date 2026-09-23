import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from xiaomusic.device_player import XiaoMusicDevice


class DownloadTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = XiaoMusicDevice.__new__(XiaoMusicDevice)
        self.player.config = SimpleNamespace(
            search_prefix="bilisearch:",
            download_path="music/download",
            proxy="",
            enable_yt_dlp_cookies=False,
            loudnorm="",
            disable_download=False,
        )
        self.player.ffmpeg_location = "./ffmpeg/bin"
        self.player.log = MagicMock()
        self.player._download_proc = None
        self.player._download_in_progress = False
        self.player.is_playing = True
        self.player.do_tts = AsyncMock()

    async def test_missing_song_uses_name_as_search_term(self):
        self.player.xiaomusic = SimpleNamespace(
            music_library=SimpleNamespace(is_music_exist=lambda name: False)
        )
        self.player.download = AsyncMock(return_value=False)
        self.player.add_download_music = AsyncMock()

        result = await self.player._check_and_download_music(
            "怒放的生命", "", allow_download=True
        )

        self.assertFalse(result)
        self.player.download.assert_awaited_once_with("怒放的生命", "怒放的生命")
        self.player.add_download_music.assert_not_awaited()
        self.assertFalse(self.player.is_playing)

    async def test_bilibili_download_passes_query_and_user_agent(self):
        proc = SimpleNamespace(wait=AsyncMock(return_value=0))
        self.player._play = AsyncMock()

        async def speak(_):
            await self.player.check_replay()

        self.player.do_tts.side_effect = speak
        with (
            patch("xiaomusic.device_player.asyncio.create_subprocess_exec", new_callable=AsyncMock) as spawn,
            patch("xiaomusic.device_player.os.path.isfile", return_value=True),
            patch("xiaomusic.device_player.chmodfile") as chmod,
        ):
            spawn.return_value = proc
            result = await self.player.download("怒放的生命", "怒放的生命")

        self.assertTrue(result)
        self.assertFalse(self.player._download_in_progress)
        self.player._play.assert_not_awaited()
        args = spawn.await_args.args
        self.assertIn("bilisearch:怒放的生命", args)
        self.assertEqual(args[args.index("--user-agent") + 1], "Mozilla/5.0")
        chmod.assert_called_once_with(
            os.path.join("music/download", "怒放的生命.mp3")
        )

    async def test_failed_download_is_not_reported_as_success(self):
        proc = SimpleNamespace(wait=AsyncMock(return_value=1))
        with (
            patch("xiaomusic.device_player.asyncio.create_subprocess_exec", new_callable=AsyncMock) as spawn,
            patch("xiaomusic.device_player.os.path.isfile", return_value=False),
            patch("xiaomusic.device_player.chmodfile") as chmod,
        ):
            spawn.return_value = proc
            result = await self.player.download("怒放的生命", "怒放的生命")

        self.assertFalse(result)
        self.assertFalse(self.player._download_in_progress)
        chmod.assert_not_called()


if __name__ == "__main__":
    unittest.main()

