library(dplyr)
library(caret)
library(sp)
library(gstat)
library(raster)
library(ggmap)
library(Metrics)

# get baltimore crime data
crime_df <- read.csv("CrimesData.csv") %>%
  dplyr::filter(grepl("2022", Date)) %>% # select 2022 data
  dplyr::select(Description, long = Longitude, lat = Latitude) # select relevant columns

# get baltimore shape file
baltimore_shp <- raster::shapefile("Shapefiles/Census_Tracts_2010.shp")

# compute crime count at each location for each type (assault/robbery/shooting/homicide/rape)
get.count <- function(df) {
  df <- df %>%
    dplyr::group_by(long, lat) %>% # group data by location
    dplyr::count() %>% # find total count for each location
    dplyr::ungroup() %>% # ungroup
    dplyr::distinct(long, lat, .keep_all = TRUE) # get unique locations
}
type <- list(
  assault = "Assault", robbery = "Robbery", shooting = "Shooting",
  homicide = "Homicide", rape = "Rape"
)
crime <- lapply(type, function(x) subset(crime_df, Description == x) %>% get.count())

# train/test split
set.seed(42)
split.data <- function(df) {
  trainIndex <- caret::createDataPartition(df$n, p = 0.75, list = FALSE)
  list(train = df[trainIndex, ], test = df[-trainIndex, ])
}
type <- list(
  assault = crime$assault, robbery = crime$robbery, shooting = crime$shooting,
  homicide = crime$homicide, rape = crime$rape
)
dl <- lapply(type, split.data)

# collect training & test data in separate lists
train <- list(
  assault = dl$assault$train, robbery = dl$robbery$train,
  shooting = dl$shooting$train, homicide = dl$homicide$train,
  rape = dl$rape$train
)
test <- list(
  assault = dl$assault$test, robbery = dl$robbery$test,
  shooting = dl$shooting$test, homicide = dl$homicide$test,
  rape = dl$rape$test
)

# compute variogram
get.variogram <- function(df, form) {
  sp::coordinates(df) <- ~ long + lat # attach coordinates
  sp::proj4string(df) <- crs(baltimore_shp) # assign longlat proj from shapefile
  v <- gstat::variogram(form, df) # empirical variogram
  vfit <- gstat::fit.variogram(v, model = vgm(model = c("Sph", "Exp", "Mat", "Gau", "Ste")))
  preds <- gstat::variogramLine(vfit, maxdist = max(v$dist)) # for plotting multiple variograms
  list(v = v, vfit = vfit, preds = preds)
}
form <- n ~ long + lat # formula for universal kriging
vg <- lapply(train, get.variogram, form)

# collect all variogram data for plotting
v_all <- data.frame(cbind(
  Distance = vg$assault$v$dist, Assault = vg$assault$v$gamma, Robbery = vg$robbery$v$gamma,
  Shooting = vg$shooting$v$gamma, Homicide = vg$homicide$v$gamma, Rape = vg$rape$v$gamma
)) %>%
  reshape2::melt(., id = "Distance", variable.name = "Crime", value.name = "Semivariance")
pred_all <- data.frame(cbind(
  Distance = vg$assault$preds$dist, Assault = vg$assault$preds$gamma,
  Robbery = vg$robbery$preds$gamma, Shooting = vg$shooting$preds$gamma,
  Homicide = vg$homicide$preds$gamma, Rape = vg$rape$preds$gamma
)) %>%
  reshape2::melt(., id = "Distance", variable.name = "Crime", value.name = "Semivariance")

# plot variogram
ggplot2::ggplot(data = pred_all, aes(x = Distance, y = Semivariance, color = Crime)) +
  geom_line() +
  geom_point(data = v_all, aes(x = Distance, y = Semivariance, color = Crime))

# function to compute kriging
run.krige <- function(df, vfit, grd, form) {
  sp::coordinates(df) <- ~ long + lat
  sp::proj4string(df) <- crs(baltimore_shp)
  krg <- gstat::krige(formula = form, locations = df, newdata = grd, model = vfit)
  data.frame(krg@coords, pred = krg@data$var1.pred)
}

# create grid from baltimore shapefile
grd <- spsample(baltimore_shp, type = "regular", n = 50000)
colnames(grd@coords) <- c("long", "lat") # rename coords

# compute kriged interpolation on grid (for training assault data)
krgout <- run.krige(train$assault, vg$assault$vfit, grd, form)

# plot kriged prediction (overlaid on Baltimore map)
ggmap::register_google(key = "<your_api_key>")
baltimore_map <- ggmap::get_map("Baltimore", zoom = 12) # get Baltimore map
plt <- ggmap::ggmap(baltimore_map) +
  geom_raster(data = krgout, mapping = aes(x = long, y = lat, fill = pred), alpha = 0.8) +
  coord_equal(expand = FALSE) +
  scale_fill_distiller(palette = "YlOrBr") +
  theme_void() +
  theme(aspect.ratio = 1)

# compare kriged and IDW predictions on a grid created from test data coordinates
# first define function to compute IDW (no variogram needed)
run.idw <- function(df, grd, form) {
  sp::coordinates(df) <- ~ long + lat
  sp::proj4string(df) <- crs(baltimore_shp)
  idwout <- gstat::idw(formula = form, locations = df, newdata = grd)
  data.frame(idwout@coords, pred = idwout@data$var1.pred)
}

# next create grid using test data coordinates
test_grd <- test$assault
sp::coordinates(test_grd) <- ~ long + lat
sp::proj4string(test_grd) <- crs(baltimore_shp)

# next compute krige and IDW predictions on this test grid
krgtest <- run.krige(train$assault, vg$assault$vfit, test_grd, form)
form <- n ~ 1      # assume homogeneous field (no spatial trend) for IDW
idwtest <- run.idw(train$assault, test_grd, form)

# compute RMSE of test data and predictions
Metrics::rmse(test$assault$n, krgtest$pred)
Metrics::rmse(test$assault$n, idwtest$pred)
