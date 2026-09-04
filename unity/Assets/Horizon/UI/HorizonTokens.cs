namespace Horizon
{
    /// <summary>COARSE-ALIGN-X tokens. Do not add decorative uses of amber/green/red.</summary>
    public static class HorizonTokens
    {
        public const string Void = "#070912";
        public const string Field = "#141a30";
        public const string LockCyan = "#7fd4e8";
        public const string DisturbanceAmber = "#e8a15c";
        public const string ConfirmGreen = "#6fe8a8";
        public const string LostRed = "#e86f7f";

        public static UnityEngine.Color VoidColor => Parse(Void);
        public static UnityEngine.Color FieldColor => Parse(Field);
        public static UnityEngine.Color LockCyanColor => Parse(LockCyan);
        public static UnityEngine.Color DisturbanceAmberColor => Parse(DisturbanceAmber);
        public static UnityEngine.Color ConfirmGreenColor => Parse(ConfirmGreen);
        public static UnityEngine.Color LostRedColor => Parse(LostRed);

        public static UnityEngine.Color Parse(string hex)
        {
            UnityEngine.Color c;
            UnityEngine.ColorUtility.TryParseHtmlString(hex, out c);
            return c;
        }
    }
}
