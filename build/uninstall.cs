using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using Microsoft.Win32;

// Launch the Inno Setup uninstaller. Never delete the source or user library.
internal static class Uninstall
{
    private const string UninstallRegistryPath = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\{6B7A3F72-45EB-4BCD-9E8A-04855EB302A1}_is1";

    private static string FindUninstaller()
    {
        string adjacent = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "unins000.exe");
        if (File.Exists(adjacent)) return adjacent;
        foreach (RegistryHive hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        {
            using (RegistryKey root = RegistryKey.OpenBaseKey(hive, view))
            using (RegistryKey key = root.OpenSubKey(UninstallRegistryPath))
            {
                if (key == null) continue;
                string location = key.GetValue("InstallLocation") as string;
                if (String.IsNullOrWhiteSpace(location)) continue;
                string candidate = Path.Combine(location, "unins000.exe");
                if (File.Exists(candidate)) return candidate;
            }
        }
        return null;
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool check = args.Length == 1 && args[0] == "--check";
        try
        {
            string path = FindUninstaller();
            if (check) return path == null ? 2 : 0;
            if (path == null)
            {
                MessageBox.Show(
                    "No installed copy of Track Separator was found.\n\n" +
                    "This folder contains source code or a portable copy, which has no installation to uninstall. " +
                    "To remove it, close the app and delete its folder after saving any audio and stems you want to keep.",
                    "Track Separator", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return 2;
            }
            Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
            return 0;
        }
        catch (Exception error)
        {
            if (!check) MessageBox.Show(error.Message, "Track Separator uninstall", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
