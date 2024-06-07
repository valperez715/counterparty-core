use std::{fs::OpenOptions, io, sync::Once};

use tracing::{level_filters::LevelFilter, Event, Subscriber};
use tracing_subscriber::{
    fmt::{
        format::Writer,
        layer,
        time::{ChronoLocal, FormatTime},
        writer::BoxMakeWriter,
        FmtContext, FormatEvent, FormatFields,
    },
    layer::SubscriberExt,
    registry::LookupSpan,
    Layer, Registry,
};

use super::config::Config;

static INIT: Once = Once::new();

#[allow(clippy::expect_used)]
pub fn setup_logging(config: &Config) {
    INIT.call_once(|| {
        let file = OpenOptions::new()
            .append(true)
            .create(true)
            .open(&config.log_file)
            .expect("Failed to open log file");

        let file_writer = BoxMakeWriter::new(file);
        let stderr_writer = BoxMakeWriter::new(io::stderr);

        let file_layer = layer()
            .json()
            .with_writer(file_writer)
            .with_filter(LevelFilter::TRACE);

        let stderr_layer = layer()
            .event_format(CustomFormatter {
                timer: ChronoLocal::new("%Y-%m-%dT-%H:%M:%S%:z".into()),
            })
            .with_writer(stderr_writer)
            .with_filter(LevelFilter::INFO);

        let subscriber = Registry::default().with(file_layer).with(stderr_layer);

        tracing::subscriber::set_global_default(subscriber)
            .expect("Failed to set global subscriber");
    });
}

struct CustomFormatter {
    pub timer: ChronoLocal,
}

impl<S, N> FormatEvent<S, N> for CustomFormatter
where
    S: Subscriber + for<'a> LookupSpan<'a>,
    N: for<'a> FormatFields<'a> + 'static,
{
    fn format_event(
        &self,
        ctx: &FmtContext<'_, S, N>,
        mut writer: Writer<'_>,
        event: &Event<'_>,
    ) -> std::fmt::Result {
        self.timer.format_time(&mut writer)?;
        let metadata = event.metadata();
        write!(writer, " - [{:>8}] - RS Fetcher - ", metadata.level())?;
        ctx.field_format().format_fields(writer.by_ref(), event)?;
        writeln!(writer)
    }
}
