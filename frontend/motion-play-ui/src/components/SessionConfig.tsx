import type { Session } from '../services/api';

interface SessionConfigProps {
    session: Session;
}

export const SessionConfig = ({ session }: SessionConfigProps) => {
    const config = session.vcnl4040_config;

    if (!config) {
        return (
            <div className="text-xs text-gray-400 italic">No config data</div>
        );
    }

    const items: { label: string; value: string }[] = [
        { label: 'Rate', value: `${config.sample_rate_hz} Hz` },
        { label: 'LED', value: String(config.led_current) },
        { label: 'Integration', value: String(config.integration_time) },
        { label: 'Resolution', value: config.high_resolution ? '16-bit' : '12-bit' },
    ];

    if (config.duty_cycle) {
        items.push({ label: 'Duty', value: String(config.duty_cycle) });
    }
    if (config.multi_pulse) {
        const mp = String(config.multi_pulse);
        items.push({ label: 'Pulses', value: mp === '1' ? '1' : mp });
    }
    if (config.read_ambient !== undefined) {
        items.push({ label: 'Ambient', value: config.read_ambient ? 'On' : 'Off' });
    }

    return (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600 px-1">
            <span className="font-medium text-gray-700 text-sm">Config</span>
            {items.map(({ label, value }) => (
                <span key={label}>
                    <span className="text-gray-500">{label}</span>{' '}
                    <span className="font-medium text-gray-800">{value}</span>
                </span>
            ))}
        </div>
    );
};